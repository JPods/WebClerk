import React, { useState } from 'react';
import { InputField, TextareaField } from '../../../../../components';
import { Audit, AUDIT_FIELD_LABELS } from '../../../types';

interface AuditFormProps {
  initialData?: Partial<Audit>;
  onSubmit: (data: Partial<Audit>) => void;
  onCancel?: () => void;
}

export const AuditForm: React.FC<AuditFormProps> = ({
  initialData = {},
  onSubmit,
  onCancel,
}) => {
  const [formData, setFormData] = useState<Partial<Audit>>(initialData);

  const handleChange = (field: keyof Audit) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData((prev: Partial<Audit>) => ({
      ...prev,
      [field]: e.target.value
    }));
  };

  const handleNumberChange = (field: keyof Audit) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData((prev: Partial<Audit>) => ({
      ...prev,
      [field]: parseInt(e.target.value) || undefined
    }));
  };

  const handleBooleanChange = (field: keyof Audit) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData((prev: Partial<Audit>) => ({
      ...prev,
      [field]: e.target.checked
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Audit Form</h2>

      <InputField
        name="purpose"
        label={AUDIT_FIELD_LABELS.purpose}
        value={formData.purpose || ''}
        onChange={handleChange('purpose')}
        placeholder="Enter purpose"
      />

      <InputField
        name="name"
        label={AUDIT_FIELD_LABELS.name}
        value={formData.name || ''}
        onChange={handleChange('name')}
        placeholder="Enter name"
      />

      <TextareaField
        name="conflicts"
        label={AUDIT_FIELD_LABELS.conflicts}
        value={typeof formData.conflicts === 'string' ? formData.conflicts : JSON.stringify(formData.conflicts, null, 2)}
        onChange={handleChange('conflicts')}
        placeholder="Enter conflicts (JSON)"
        rows={3}
      />

      <TextareaField
        name="changes"
        label={AUDIT_FIELD_LABELS.changes}
        value={typeof formData.changes === 'string' ? formData.changes : JSON.stringify(formData.changes, null, 2)}
        onChange={handleChange('changes')}
        placeholder="Enter changes (JSON)"
        rows={3}
      />

      <TextareaField
        name="actions"
        label={AUDIT_FIELD_LABELS.actions}
        value={typeof formData.actions === 'string' ? formData.actions : JSON.stringify(formData.actions, null, 2)}
        onChange={handleChange('actions')}
        placeholder="Enter actions (JSON)"
        rows={3}
      />

      <TextareaField
        name="recommendations"
        label={AUDIT_FIELD_LABELS.recommendations}
        value={typeof formData.recommendations === 'string' ? formData.recommendations : JSON.stringify(formData.recommendations, null, 2)}
        onChange={handleChange('recommendations')}
        placeholder="Enter recommendations (JSON)"
        rows={3}
      />

      <InputField
        name="rating"
        label={AUDIT_FIELD_LABELS.rating}
        type="number"
        value={formData.rating?.toString() || ''}
        onChange={handleNumberChange('rating')}
        placeholder="Enter rating"
      />

      <div className="flex items-center">
        <input
          id="is_completed"
          name="is_completed"
          type="checkbox"
          checked={formData.is_completed || false}
          onChange={handleBooleanChange('is_completed')}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="is_completed" className="ml-2 block text-sm text-gray-900">
          {AUDIT_FIELD_LABELS.is_completed}
        </label>
      </div>

      <InputField
        name="priority"
        label={AUDIT_FIELD_LABELS.priority}
        type="number"
        value={formData.priority?.toString() || ''}
        onChange={handleNumberChange('priority')}
        placeholder="Enter priority"
      />

      <div className="flex space-x-4 pt-4">
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Submit
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
};

export default AuditForm;