import { useEffect, useState } from 'react';
import { fetchCustomers, updateCustomer } from '../services/customerApi';
import { useForm, Controller } from 'react-hook-form';
import { useState as useLocalState } from 'react';


export const CustomerDashboard = () => {
  const [customer, setCustomer] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchCustomers(81)
      .then((res) => {
        // The API returns the customer in res.data or res.data.data
        const data = res?.data?.data || res?.data || res;
        if (!data || (Array.isArray(data) && data.length === 0)) {
          throw new Error('Customer not found');
        }
        // If array, take first; else use as is
        setCustomer(Array.isArray(data) ? data[0] : data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch customer');
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <h2>Customer Dashboard</h2>
      {loading && <div>Loading customer data...</div>}
      {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      {customer && (
        <CustomerEditForm customer={customer} onSaveSuccess={setCustomer} />
      )}

    </div>
  );
};

// Editable form fields
const scalarFields = [
  "company",
  "display_name",
  "id",
  "is_active",
  "status",
  "version",
  "dt_created",
  "dt_modified",
];
const objectFields = [
  "contacts",
  "data",
  "domains",
  "emails",
  "financial",
  "addresses",
  "phones",
  "relations",
];

export function CustomerEditForm({ customer, onSaveSuccess }: { customer: any, onSaveSuccess: (c: any) => void }) {
      const { register, handleSubmit, control, formState: { isSubmitting } } = useForm({
        defaultValues: customer
      });
      const [error, setError] = useLocalState<string | null>(null);
      const [success, setSuccess] = useLocalState<string | null>(null);

      const onSubmit = async (formData: any) => {
        setError(null);
        setSuccess(null);
        try {
          // Parse JSON fields for object fields
          const payload = { ...formData };
          objectFields.forEach((field) => {
            try {
              payload[field] = JSON.parse(formData[field] || '{}');
            } catch {
              payload[field] = {};
            }
          });
           const updated = await updateCustomer(payload);
           if (updated) {
             setSuccess('Customer updated successfully.');
             onSaveSuccess(updated);
           } else {
             setError('Update failed.');
           }
        } catch (e: any) {
          setError(e.message || 'Update failed.');
        }
      };

      return (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <h3>Edit Customer</h3>
          {error && <div style={{ color: 'red' }}>{error}</div>}
          {success && <div style={{ color: 'green' }}>{success}</div>}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {scalarFields.map((field) => (
              <div key={field}>
                <label className="block text-xs font-semibold mb-1" htmlFor={field}>{field}</label>
                <input
                  id={field}
                  {...register(field)}
                  className="w-full border rounded px-2 py-1 text-sm"
                  disabled={field === 'id' || field === 'dt_created' || field === 'dt_modified'}
                />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {objectFields.map((field) => (
              <div key={field}>
                <label className="block text-xs font-semibold mb-1" htmlFor={field}>{field} (JSON)</label>
                <Controller
                  name={field}
                  control={control}
                  defaultValue={JSON.stringify(customer[field] || {}, null, 2)}
                  render={({ field: ctrlField }) => (
                    <textarea
                      id={field}
                      {...ctrlField}
                      rows={6}
                      className="w-full border rounded px-2 py-1 font-mono text-xs"
                      spellCheck={false}
                    />
                  )}
                />
              </div>
            ))}
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-60"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving...' : 'Save'}
          </button>
        </form>
      );
}
