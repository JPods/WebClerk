from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal
from common.models import BaseModel
from apps.transactions.choices import PROJECT_ATTENTION_CHOICES, PROJECT_STATUS_CHOICES


# Color palette for projects (matches frontend GanttProjectSelector.tsx)
PROJECT_COLOR_PALETTE = [
    "#3b82f6",  # blue-500
    "#10b981",  # emerald-500
    "#f59e0b",  # amber-500
    "#ef4444",  # red-500
    "#8b5cf6",  # violet-500
    "#ec4899",  # pink-500
    "#06b6d4",  # cyan-500
    "#84cc16",  # lime-500
    "#f97316",  # orange-500
    "#6366f1",  # indigo-500
]


def default_objective():  # lightweight structured goal definition
    return {
        "summary": "",
        "success": {"definition": "", "metrics": []},
        "scope": {"in": [], "out": []},
    }


def default_tasks():  # simple backlog skeleton
    return {
        "items": [],  # each: {id:int, title:str, done:bool, weight:int, eta_days:int?}
        "completed": 0,
        "total": 0,
    }


def default_logistics():
    return {"budget": 0.0, "deadline": 0, "timezone": "", "resources": []}


def default_data():  # project-specific arbitrary data (kept distinct from BaseModel.data)
    return {}


STATUS_CHOICES = PROJECT_STATUS_CHOICES

ATTENTION_CHOICES = PROJECT_ATTENTION_CHOICES

PRIORITY_MIN = 1
PRIORITY_MAX = 5


class Project(BaseModel):
    """Cross-document initiative / scrum-style aggregator.

    Intent: unify related transactions (proposals, orders...) and actions under
    a single planning / governance artifact. Uses BaseModel envelopes for
    metadata, prefs, refs, comments, etc.
    """
    name = models.CharField(max_length=255, blank=True, default="", help_text="Short name or title")
    dt_kanban = models.DateTimeField(null=True, blank=True, db_index=True, help_text="Next action / review date for prioritization")
    situation = models.TextField(blank=True, default="", help_text="Current context / problem narrative")
    objective = models.JSONField(default=default_objective, help_text="Structured goal & success metrics")
    priority = models.PositiveSmallIntegerField(default=3, help_text="1 (highest) – 5 (lowest)")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", db_index=True)
    attention = models.CharField(max_length=16, choices=ATTENTION_CHOICES, default="normal", db_index=True)
    id_contact = models.BigIntegerField(null=True, blank=True, db_index=True, help_text="Owning / primary contact id")
    tasks = models.JSONField(default=default_tasks, help_text="Backlog tasks + derived counters")
    burndown = models.PositiveSmallIntegerField(default=0, help_text="0-100 percent completion snapshot")
    category = models.CharField(max_length=128, blank=True, default="", db_index=True)
    intent = models.CharField(max_length=255, blank=True, default="", help_text="Short intent tagline / elevator pitch")
    logistics = models.JSONField(default=default_logistics, help_text="Budget / schedule / resource data")
    slug = models.CharField(max_length=180, blank=True, null=True, db_index=True, help_text="URL / human friendly identifier derived from intent")
    profit = models.DecimalField(default=Decimal('0.00'), max_digits=14, decimal_places=2, help_text="Projected or realized profit (base currency with cents)")
    profit_velocity = models.IntegerField(default=0, help_text="Profit per time unit (arbitrary) for trend")
    # Allow NULL so callers can intentionally distinguish "no payload yet" vs empty structure
    config = models.JSONField(default=default_data, blank=True, null=True, help_text="Arbitrary project-specific data payload (nullable)")
    # Timeline and hierarchy (added 2026-07-29)
    dt_start = models.BigIntegerField(default=0, help_text="Project start date (epoch ms)")
    dt_end = models.BigIntegerField(default=0, help_text="Project end date (epoch ms)")
    id_parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_parent', related_name='children',
        help_text="Parent project for hierarchy",
    )
    percent_complete = models.IntegerField(default=0, help_text="0-100 completion percentage")

    def __str__(self):
        return self.name or f"Project {self.id}"

    class Meta:
        db_table = "projects"
        indexes = [
            models.Index(fields=["status"], name="project_status_idx"),
            models.Index(fields=["priority"], name="project_priority_idx"),
            models.Index(fields=["attention"], name="project_attention_idx"),
            models.Index(fields=["category"], name="project_category_idx"),
            models.Index(fields=["id_contact"], name="project_contact_idx"),
            models.Index(fields=["status", "priority"], name="project_status_priority_idx"),
            models.Index(fields=["slug"], name="project_slug_idx"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(priority__gte=PRIORITY_MIN, priority__lte=PRIORITY_MAX), name="project_priority_range"),
            models.CheckConstraint(check=models.Q(burndown__gte=0, burndown__lte=100), name="project_burndown_range"),
        ]

    # -------- Derived / validation helpers ---------------------------------
    def _recompute_task_counters(self):
        t = self.tasks or {}
        items = t.get("items") if isinstance(t, dict) else None
        if isinstance(items, list):
            total = len(items)
            done = sum(1 for it in items if isinstance(it, dict) and it.get("done"))
            # weighted progress (default weight=1)
            weight_total = 0
            weight_done = 0
            for it in items:
                if not isinstance(it, dict):
                    continue
                w = int(it.get("weight", 1) or 1)
                weight_total += w
                if it.get("done"):
                    weight_done += w
            t["total"] = total
            t["completed"] = done
            t["weight_total"] = weight_total
            t["weight_completed"] = weight_done
            self.tasks = t
            # auto update burndown only if user hasn't explicitly set a different one in current instance
            if total:
                if weight_total > 0:
                    computed = int((weight_done / weight_total) * 100)
                else:
                    computed = int((done / total) * 100)
                # allow slight drift if user wants manual override (only overwrite if difference > 2%)
                if abs(computed - (self.burndown or 0)) > 2:
                    self.burndown = computed

    def clean(self):
        errors = {}
        if not (PRIORITY_MIN <= (self.priority or 0) <= PRIORITY_MAX):
            errors['priority'] = f"Priority must be {PRIORITY_MIN}-{PRIORITY_MAX}"
        if not (0 <= (self.burndown or 0) <= 100):
            errors['burndown'] = "Burndown must be 0-100"
        if errors:
            raise ValidationError(errors)

    def _get_next_palette_color(self):
        """Get the next color from the palette based on existing colored projects.
        
        Cycles through the palette so colors repeat if there are more projects than colors.
        """
        # Count existing active projects that already have a color assigned (excluding self)
        projects_with_colors = 0
        for proj in Project.objects.filter(is_active=True).exclude(pk=self.pk):
            prefs = proj.prefs or {}
            if isinstance(prefs, dict):
                action_prefs = prefs.get('action', {})
                if isinstance(action_prefs, dict) and action_prefs.get('color'):
                    projects_with_colors += 1
        return PROJECT_COLOR_PALETTE[projects_with_colors % len(PROJECT_COLOR_PALETTE)]

    def _ensure_action_color(self):
        """Auto-assign prefs.action.color if not already set.
        
        Administrators can manually override by setting prefs.action.color explicitly.
        """
        prefs = getattr(self, 'prefs', None) or {}
        if not isinstance(prefs, dict):
            prefs = {}
        
        # Check if action.color is already set
        action_prefs = prefs.get('action', {})
        if isinstance(action_prefs, dict) and action_prefs.get('color'):
            # Color already set, don't override (allows admin manual override)
            return
        
        # Auto-assign color from palette
        color = self._get_next_palette_color()
        
        # Ensure nested structure exists
        if 'action' not in prefs or not isinstance(prefs.get('action'), dict):
            prefs['action'] = {}
        prefs['action']['color'] = color
        
        self.prefs = prefs

    def _ensure_gantt_weight(self):
        """Auto-assign prefs.gantt.weight if not already set.

        0 = hidden, 1-2 = low, 3 = normal (default), 4-5 = pinned to top.
        Child projects default to 0 (hidden). Top-level default to 3.
        """
        prefs = getattr(self, 'prefs', None) or {}
        if not isinstance(prefs, dict):
            prefs = {}
        gantt = prefs.get('gantt', {})
        if not isinstance(gantt, dict):
            gantt = {}
        if 'weight' in gantt:
            return
        gantt['weight'] = 0 if self.id_parent else 3
        prefs['gantt'] = gantt
        self.prefs = prefs

    def save(self, *args, **kwargs):
        # derive counters & validate
        if not self.slug and self.intent:
            self.slug = slugify(self.intent)[:180]

        # Auto-assign action color if not set
        self._ensure_action_color()
        self._ensure_gantt_weight()
        
        self._recompute_task_counters()
        self.full_clean(exclude=None)
        super().save(*args, **kwargs)

    # convenience
    def add_task(self, title: str, weight: int = 1):
        t = self.tasks
        if not isinstance(t, dict):
            t = default_tasks()
        items = t.setdefault('items', [])
        next_id = (max([it.get('id', 0) for it in items], default=0) + 1) if items else 1
        items.append({"id": next_id, "title": title, "done": False, "weight": weight})
        self.tasks = t
        self._recompute_task_counters()
        return next_id

    def mark_task_done(self, task_id: int):
        t = self.tasks
        if isinstance(t, dict):
            for it in t.get('items', []):
                if it.get('id') == task_id:
                    it['done'] = True
                    break
            self.tasks = t
            self._recompute_task_counters()
        return self.burndown


