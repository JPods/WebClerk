"""
Management command: ai_health

Check the health of the AI assistant system (Ollama, vector store, etc.).

Usage:
    python manage.py ai_health
"""
from django.core.management.base import BaseCommand
from apps.ai_assistant.services.rag import RAGService


class Command(BaseCommand):
    help = "Check AI assistant health: Ollama connection, model availability, vector store status"

    def handle(self, *args, **options):
        rag = RAGService()
        health = rag.health_check()

        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(self.style.HTTP_INFO("AI Assistant Health Check"))
        self.stdout.write(f"{'='*50}")

        # Ollama status
        if health["ollama_available"]:
            self.stdout.write(self.style.SUCCESS(
                f"  Ollama: CONNECTED ({health['ollama_url']})"
            ))
            self.stdout.write(f"  Model: {health['ollama_model']}")
            self.stdout.write(f"  Available models: {', '.join(health['available_models'])}")
        else:
            self.stdout.write(self.style.ERROR(
                f"  Ollama: NOT AVAILABLE ({health['ollama_url']})"
            ))
            self.stdout.write(self.style.WARNING(
                "  Fix: Run 'ollama serve' and 'ollama pull deepseek-coder-v2'"
            ))

        # Vector store status
        vs = health["vector_store"]
        if vs["count"] > 0:
            self.stdout.write(self.style.SUCCESS(
                f"  Vector store: {vs['count']} chunks indexed"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "  Vector store: EMPTY"
            ))
            self.stdout.write(self.style.WARNING(
                "  Fix: Run 'python manage.py index_docs'"
            ))

        # Overall status
        self.stdout.write(f"\n  Overall: {health['status'].upper()}")
        if health["status"] != "ok":
            self.stdout.write(self.style.WARNING(
                "\n  Run 'python manage.py setup_ai' for automated setup."
            ))
