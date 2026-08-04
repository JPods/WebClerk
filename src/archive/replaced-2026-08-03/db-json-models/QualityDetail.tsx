/**
 * QualityDetail.tsx — Single detail page for all quality record types.
 *
 * This is an Action record view. The metadata.quality_type field determines
 * which form sections render. One place to look. One model. One DataBrowser.
 *
 * Workflow steps advance via the Step indicator — Alice tracks transitions.
 */
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  FileWarning, ClipboardCheck, GitBranch, FileText, HelpCircle,
} from 'lucide-react';

import ComponentCard from '@/components/common/ComponentCard';
import HorizontalField from '@/components/form/HorizontalField';
import { Input } from '@/components/wrapper';
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import { SimpleDetailHeader } from '@/components/common/SimpleDetailHeader';
import { SimpleDetailToolbar } from '@/components/common/SimpleDetailToolbar';
import { DetailTabs, useDetailTabs } from '@/components/common/DetailTabs';
import { ScalarCard, JsonCard, BaseModelCards } from '@/apps/common/components/detail';
import { showToast } from '@/store/slices/toastSlice';
import { useDispatch } from 'react-redux';
import { useLocation, useNavigate } from 'react-router';

import type { QualityPageProps, QualityType } from '../types/qualityTypes';
import { QUALITY_LABELS, WORKFLOW_STEPS } from '../types/qualityTypes';
import { QUALITY_SCHEMAS } from '../utils/qualitySchema';
import {
  createQualityRecord, updateQualityRecord,
  nextQualityNumber, advanceWorkflow,
} from '../services/qualityApi';

// ── Workflow Step Indicator ──────────────────────────────────────────

function StepIndicator({ steps, current }: { steps: string[]; current: string }) {
  const idx = steps.indexOf(current);
  return (
    <div className="flex items-center gap-1 mb-4 text-xs">
      {steps.map((step, i) => (
        <div key={step} className="flex items-center gap-1">
          <span className={`px-2 py-1 rounded ${
            i < idx ? 'bg-green-100 text-green-700' :
            i === idx ? 'bg-blue-600 text-white font-semibold' :
            'bg-gray-100 text-gray-400'
          }`}>
            {step.replace(/_/g, ' ')}
          </span>
          {i < steps.length - 1 && <span className="text-gray-300">→</span>}
        </div>
      ))}
    </div>
  );
}

// ── Type icon ────────────────────────────────────────────────────────

const TYPE_ICONS: Record<QualityType, any> = {
  ncr: FileWarning,
  car: ClipboardCheck,
  deviation: GitBranch,
  dcr: FileText,
  request: HelpCircle,
};

// ── Main Component ───────────────────────────────────────────────────

export default function QualityDetail({
  modeProp,
  dataProp,
  qualityType: qualityTypeProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: QualityPageProps) {
  const dispatch = useDispatch();
  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as any) || {};

  const data = dataProp || routeState.data || null;
  const initialMode: 'add' | 'edit' | 'view' = modeProp || routeState.mode || 'add';
  const [currentMode, setCurrentMode] = useState(initialMode);
  const [isSaving, setIsSaving] = useState(false);
  const [recordData, setRecordData] = useState<any>(data || {});

  // Determine quality type from data or prop
  const qualityType: QualityType =
    qualityTypeProp ||
    recordData?.metadata?.quality_type ||
    routeState.qualityType ||
    'request';

  const schema = QUALITY_SCHEMAS[qualityType] || QUALITY_SCHEMAS.request;
  const steps = WORKFLOW_STEPS[qualityType];
  const currentStep = recordData?.metadata?.workflow_step || steps[0];
  const Icon = TYPE_ICONS[qualityType];

  const {
    register, setValue, handleSubmit, formState: { errors }, reset,
  } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (data) {
      Object.entries(data).forEach(([key, val]) => {
        try { setValue(key as any, val as any); } catch {}
      });
      // Flatten metadata into form fields
      if (data.metadata) {
        Object.entries(data.metadata).forEach(([key, val]) => {
          try { setValue(key as any, val as any); } catch {}
        });
      }
      setRecordData(data);
    }
  }, [data]);

  const onSubmit = async (formData: any) => {
    setIsSaving(true);
    try {
      // Separate Action base fields from metadata
      const { task, description, status, priority, project_name, ...metaFields } = formData;
      const qualityNumber = recordData?.metadata?.quality_number || await nextQualityNumber(qualityType);

      const metadata = {
        ...recordData?.metadata,
        ...metaFields,
        quality_type: qualityType,
        quality_number: qualityNumber,
        workflow_step: currentStep,
      };

      if (currentMode === 'add') {
        const result = await createQualityRecord(qualityType, task, description, metadata, {
          status: status || 'open',
          priority: priority || 5,
          project_name: project_name || 'Quality',
        });
        dispatch(showToast({ message: `${QUALITY_LABELS[qualityType]} ${qualityNumber} created`, type: 'success' }));
        setRecordData(result);
        setCurrentMode('edit');
      } else {
        await updateQualityRecord(recordData.id, {
          task, description, status, priority, metadata,
        });
        dispatch(showToast({ message: `${QUALITY_LABELS[qualityType]} updated`, type: 'success' }));
      }
      onSaved?.();
    } catch (err: any) {
      dispatch(showToast({ message: err.message || 'Save failed', type: 'error' }));
    } finally {
      setIsSaving(false);
    }
  };

  const handleAdvance = async () => {
    const idx = steps.indexOf(currentStep);
    if (idx < steps.length - 1) {
      const next = steps[idx + 1];
      await advanceWorkflow(recordData.id, next);
      setRecordData((prev: any) => ({
        ...prev,
        metadata: { ...prev.metadata, workflow_step: next },
      }));
      dispatch(showToast({ message: `Advanced to: ${next.replace(/_/g, ' ')}`, type: 'success' }));
    }
  };

  // ── Tab configuration ──

  const tabs = [
    { id: 'detail', label: QUALITY_LABELS[qualityType] },
    { id: 'metadata', label: 'Metadata' },
    ...(currentMode !== 'add' ? [{ id: 'history', label: 'History' }] : []),
  ];
  const { activeTab, setActiveTab } = useDetailTabs(tabs);

  const isView = currentMode === 'view';

  return (
    <div className="p-4">
      {!hideBreadcrumb && (
        <PageBreadcrumb
          pageTitle={QUALITY_LABELS[qualityType]}
          items={[
            { label: 'Support', path: '/support' },
            { label: 'Quality', path: '/support/quality' },
          ]}
        />
      )}

      <SimpleDetailHeader
        icon={<Icon size={20} />}
        title={recordData?.metadata?.quality_number || `New ${QUALITY_LABELS[qualityType]}`}
        subtitle={recordData?.task || ''}
      />

      {currentMode !== 'add' && (
        <StepIndicator steps={steps} current={currentStep} />
      )}

      <SimpleDetailToolbar
        mode={currentMode}
        onEdit={() => setCurrentMode('edit')}
        onCancel={() => {
          if (inline) onCancelInline?.();
          else { setCurrentMode('view'); reset(); }
        }}
        onSave={handleSubmit(onSubmit)}
        isSaving={isSaving}
        extraButtons={
          currentMode === 'edit' && currentStep !== steps[steps.length - 1] ? (
            <button type="button" onClick={handleAdvance}
                    className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
              Advance →
            </button>
          ) : undefined
        }
      />

      <DetailTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'detail' && (
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* ── Common fields (all types) ── */}
          <ComponentCard title="Record">
            <HorizontalField label="Title" error={errors.task?.message}>
              <Input {...register('task')} disabled={isView} placeholder="Short description" />
            </HorizontalField>
            <HorizontalField label="Description" error={errors.description?.message}>
              <textarea {...register('description')} disabled={isView} rows={3}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            </HorizontalField>
            <div className="grid grid-cols-2 gap-4">
              <HorizontalField label="Status">
                <select {...register('status')} disabled={isView}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="closed">Closed</option>
                </select>
              </HorizontalField>
              <HorizontalField label="Priority">
                <Input type="number" {...register('priority', { valueAsNumber: true })}
                  disabled={isView} min={1} max={10} />
              </HorizontalField>
            </div>
          </ComponentCard>

          {/* ── Originator (all types) ── */}
          <ComponentCard title="Originator">
            <div className="grid grid-cols-2 gap-4">
              <HorizontalField label="Name" error={errors.originator_name?.message}>
                <Input {...register('originator_name')} disabled={isView} />
              </HorizontalField>
              <HorizontalField label="Organization">
                <Input {...register('originator_org')} disabled={isView} />
              </HorizontalField>
              <HorizontalField label="Email" error={errors.originator_email?.message}>
                <Input type="email" {...register('originator_email')} disabled={isView} />
              </HorizontalField>
              <HorizontalField label="Phone">
                <Input {...register('originator_phone')} disabled={isView} />
              </HorizontalField>
            </div>
          </ComponentCard>

          {/* ── NCR-specific ── */}
          {qualityType === 'ncr' && (
            <>
              <ComponentCard title="Nonconformance">
                <div className="grid grid-cols-2 gap-4">
                  <HorizontalField label="Item Name" error={(errors as any).item_name?.message}>
                    <Input {...register('item_name')} disabled={isView} />
                  </HorizontalField>
                  <HorizontalField label="Qty">
                    <Input type="number" {...register('item_qty')} disabled={isView} />
                  </HorizontalField>
                  <HorizontalField label="Drawing / Part No.">
                    <Input {...register('drawing_part_no')} disabled={isView} />
                  </HorizontalField>
                  <HorizontalField label="Lot / Serial No.">
                    <Input {...register('lot_serial_no')} disabled={isView} />
                  </HorizontalField>
                </div>
                <HorizontalField label="Found During">
                  <Input {...register('found_during')} disabled={isView} />
                </HorizontalField>
                <HorizontalField label="Actual Condition" error={(errors as any).actual_condition?.message}>
                  <textarea {...register('actual_condition')} disabled={isView} rows={3}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
                <HorizontalField label="Required Condition" error={(errors as any).required_condition?.message}>
                  <textarea {...register('required_condition')} disabled={isView} rows={3}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
              </ComponentCard>
              <ComponentCard title="Disposition">
                <HorizontalField label="Disposition">
                  <select {...register('disposition')} disabled={isView}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                    <option value="">— Select —</option>
                    <option value="rework">Rework to Original Spec</option>
                    <option value="scrap">Scrap</option>
                    <option value="return_to_supplier">Return to Supplier</option>
                    <option value="repair">Repair</option>
                    <option value="regrade">Regrade</option>
                    <option value="use_as_is">Use As Is</option>
                  </select>
                </HorizontalField>
                <HorizontalField label="Cause">
                  <select {...register('cause')} disabled={isView}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                    <option value="">— Select —</option>
                    <option value="design">Design</option>
                    <option value="manufacturing">Manufacturing</option>
                    <option value="supplier">Supplier</option>
                    <option value="training">Training</option>
                    <option value="other">Other</option>
                  </select>
                </HorizontalField>
                <HorizontalField label="Disposition Rationale">
                  <textarea {...register('disposition_rationale')} disabled={isView} rows={2}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
              </ComponentCard>
            </>
          )}

          {/* ── CAR-specific ── */}
          {qualityType === 'car' && (
            <>
              <ComponentCard title="Corrective Action">
                <HorizontalField label="Action Type" error={(errors as any).action_type?.message}>
                  <select {...register('action_type')} disabled={isView}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                    <option value="">— Select —</option>
                    <option value="corrective">Corrective (existing)</option>
                    <option value="preventive">Preventive (potential)</option>
                    <option value="audit">Audit Nonconformance</option>
                  </select>
                </HorizontalField>
                <HorizontalField label="Discrepancy" error={(errors as any).discrepancy?.message}>
                  <textarea {...register('discrepancy')} disabled={isView} rows={4}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
                <HorizontalField label="Root Cause">
                  <textarea {...register('root_cause')} disabled={isView} rows={3}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
                <HorizontalField label="Proposed Action">
                  <textarea {...register('proposed_action')} disabled={isView} rows={3}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
                <HorizontalField label="Action Taken">
                  <textarea {...register('action_taken')} disabled={isView} rows={3}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
                </HorizontalField>
              </ComponentCard>
            </>
          )}

          {/* ── Deviation-specific ── */}
          {qualityType === 'deviation' && (
            <ComponentCard title="Deviation / Waiver">
              <HorizontalField label="Type" error={(errors as any).request_type?.message}>
                <select {...register('request_type')} disabled={isView}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                  <option value="">— Select —</option>
                  <option value="deviation">Deviation</option>
                  <option value="waiver">Waiver</option>
                </select>
              </HorizontalField>
              <div className="grid grid-cols-3 gap-4">
                <HorizontalField label="Department">
                  <Input {...register('department')} disabled={isView} />
                </HorizontalField>
                <HorizontalField label="Project">
                  <Input {...register('project_name')} disabled={isView} />
                </HorizontalField>
                <HorizontalField label="Subsystem">
                  <Input {...register('subsystem')} disabled={isView} />
                </HorizontalField>
              </div>
              <HorizontalField label="Justification" error={(errors as any).justification?.message}>
                <textarea {...register('justification')} disabled={isView} rows={4}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
              </HorizontalField>
            </ComponentCard>
          )}

          {/* ── DCR-specific ── */}
          {qualityType === 'dcr' && (
            <ComponentCard title="Document Change">
              <HorizontalField label="Action Type" error={(errors as any).action_type?.message}>
                <select {...register('action_type')} disabled={isView}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm">
                  <option value="">— Select —</option>
                  <option value="new">New Document</option>
                  <option value="revision">Revision</option>
                  <option value="cancellation">Cancellation</option>
                  <option value="supersedes">Supersedes Previous</option>
                </select>
              </HorizontalField>
              <div className="grid grid-cols-2 gap-4">
                <HorizontalField label="Document Number">
                  <Input {...register('doc_number')} disabled={isView} />
                </HorizontalField>
                <HorizontalField label="Document Title">
                  <Input {...register('doc_title')} disabled={isView} />
                </HorizontalField>
              </div>
              <HorizontalField label="Summary" error={(errors as any).summary?.message}>
                <textarea {...register('summary')} disabled={isView} rows={3}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
              </HorizontalField>
              <HorizontalField label="Detailed Description">
                <textarea {...register('detail')} disabled={isView} rows={4}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm" />
              </HorizontalField>
            </ComponentCard>
          )}

          {/* ── Request-specific ── */}
          {qualityType === 'request' && (
            <ComponentCard title="Request Target">
              <HorizontalField label="Organization" error={(errors as any).target_org?.message}>
                <Input {...register('target_org')} disabled={isView}
                  placeholder="e.g. Rhode Island DOT" />
              </HorizontalField>
              <div className="grid grid-cols-2 gap-4">
                <HorizontalField label="Contact">
                  <Input {...register('target_contact')} disabled={isView} />
                </HorizontalField>
                <HorizontalField label="Portal URL">
                  <Input {...register('target_portal_url')} disabled={isView}
                    placeholder="https://..." />
                </HorizontalField>
              </div>
              <HorizontalField label="Legal Basis">
                <Input {...register('legal_basis')} disabled={isView}
                  placeholder="FOIA, APRA, Commercial Agreement, etc." />
              </HorizontalField>
              <HorizontalField label="Follow-up (days)">
                <Input type="number" {...register('follow_up_days', { valueAsNumber: true })}
                  disabled={isView} min={1} max={90} />
              </HorizontalField>
            </ComponentCard>
          )}
        </form>
      )}

      {activeTab === 'metadata' && recordData && (
        <BaseModelCards record={recordData} />
      )}

      {activeTab === 'history' && recordData && (
        <ComponentCard title="Workflow History">
          <p className="text-sm text-gray-500">
            Action #{recordData.id} — Created {recordData.dt_created}
            {recordData.parent_action && ` — Child of Action #${recordData.parent_action}`}
          </p>
        </ComponentCard>
      )}
    </div>
  );
}
