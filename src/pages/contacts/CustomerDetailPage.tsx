import { useEffect, useState } from "react";
import { useParams } from "react-router";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import CustomerForm from "../../components/CustomerForm";
import OrdersList from "../../components/OrdersList";
import InvoicesList from "../../components/InvoicesList";
import ProposalsList from "../../components/ProposalsList";
import QAList from "../../components/QAList";
import { getRecord } from "../../api/wcapi";

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [customer, setCustomer] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchCustomer();
    } else {
      setLoading(false);
    }
  }, [id]);

  const fetchCustomer = async () => {
    try {
      const res = await getRecord('contact', parseInt(id!));
      setCustomer(res.record);
    } catch (error) {
      console.error("Failed to fetch customer", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <>
      <PageBreadcrumb pageTitle="Customer Details" />
      <div className="space-y-6">
        {/* Locked Box Placeholder */}
        <ComponentCard>
          <div className="p-4 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded">
            Locked Box Component - Placeholder
          </div>
        </ComponentCard>

        {/* Customer Form */}
        <CustomerForm
          modeProp={id ? 'edit' : 'add'}
          dataProp={customer}
          onSaved={() => {
            if (id) fetchCustomer();
          }}
        />

        {/* Orders List */}
        <ComponentCard>
          <OrdersList customerId={customer?.id} />
        </ComponentCard>

        {/* Cloneable Proposals Button */}
        <div className="flex justify-center">
          <button className="btn btn-primary">
            Cloneable Proposals
          </button>
        </div>

        {/* Proposals List */}
        <ComponentCard>
          <ProposalsList customerId={customer?.id} />
        </ComponentCard>

        {/* Invoices List */}
        <ComponentCard>
          <InvoicesList customerId={customer?.id} />
        </ComponentCard>

        {/* QA List */}
        <ComponentCard>
          <QAList entityType="contact" entityId={customer?.id} />
        </ComponentCard>

        {/* QA Form Placeholder */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">QA Form</h3>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
            QA Form Component - Placeholder (Modal for editing QA)
          </div>
        </ComponentCard>
      </div>
    </>
  );
}