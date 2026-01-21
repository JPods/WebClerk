import React, { useEffect, useState } from 'react';

// Placeholder containers for each dashboard section
const ScalarData = () => <section><h3>Customer Data</h3>{/* Scalar & dotted object data */}</section>;
const ContactContainer = () => <section><h3>Contact Information</h3>{/* Add/Edit email, phone, domain, address */}</section>;
const BusinessObjects = () => <section><h3>Proposals, Orders, Invoices, Payments, Ledgers, Projects</h3>{/* Related records */}</section>;
const CommentsContainer = () => <section><h3>Comments</h3>{/* View/Add comments */}</section>;
const PrefsContainer = () => <section><h3>Preferences</h3>{/* View/Edit .prefs */}</section>;
const ActionsContainer = () => <section><h3>Actions</h3>{/* View/Edit actions */}</section>;
const LinkageContainer = () => <section><h3>Linkage</h3>{/* View/Edit linkage */}</section>;
const DocumentContainer = () => <section><h3>Documents</h3>{/* View/Edit documents */}</section>;
const QAContainer = () => <section><h3>Q&A</h3>{/* View/Edit question_answer */}</section>;
const TagContainer = () => <section><h3>Tags</h3>{/* View/Edit tags */}</section>;
const ProductsContainer = () => <section><h3>Products/Serials</h3>{/* View/Edit products/serials */}</section>;
const RelationshipsContainer = () => <section><h3>Relationships</h3>{/* Vendor, Manufacturer, Rep, Employee */}</section>;
const CatalogsContainer = () => <section><h3>Catalogs</h3>{/* View/Edit catalogs */}</section>;
const CampaignsContainer = () => <section><h3>Campaigns</h3>{/* View/Edit campaigns */}</section>;

  const [customer, setCustomer] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    // Replace with your real API endpoint
    fetch(`/api/customers/81`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch customer');
        return res.json();
      })
      .then((data) => {
        setCustomer(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div>
      <h2>Customer Dashboard</h2>
      {loading && <div>Loading customer data...</div>}
      {error && <div style={{ color: 'red' }}>Error: {error}</div>}
      {customer && (
        <pre style={{ background: '#f6f8fa', padding: 12, borderRadius: 4 }}>
          {JSON.stringify(customer, null, 2)}
        </pre>
      )}
      {/* Placeholder containers below */}
      <ScalarData />
      <ContactContainer />
      <BusinessObjects />
      <CommentsContainer />
      <PrefsContainer />
      <ActionsContainer />
      <LinkageContainer />
      <DocumentContainer />
      <QAContainer />
      <TagContainer />
      <ProductsContainer />
      <RelationshipsContainer />
      <CatalogsContainer />
      <CampaignsContainer />
    </div>
  );
};
