import PageBreadcrumb from "../components/common/PageBreadCrumb";
import UserMetaCard from "../components/UserProfile/UserMetaCard";
import UserInfoCard from "../components/UserProfile/UserInfoCard";
import UserAddressCard from "../components/UserProfile/UserAddressCard";
import PageMeta from "../components/common/PageMeta";

import React, { useState } from 'react';
import { ChevronDown, Mail, Phone, MapPin, Calendar, Link, Plus } from 'lucide-react';

// Reusable Input Field Component
const InputField = ({ label, placeholder, icon, type = "text", value, onChange, className = "" }) => (
  <div className={`flex items-center space-x-3 bg-white p-3 rounded-md shadow-sm border border-gray-200 ${className}`}>
    {icon && <div className="text-gray-500">{icon}</div>}
    <input
      type={type}
      placeholder={placeholder}
      className="flex-grow outline-none bg-transparent text-gray-800"
      aria-label={label}
      value={value}
      onChange={onChange}
    />
  </div>
);

// Reusable Add Button Component
const AddButton = ({ label, onClick, icon }) => (
  <button
    onClick={onClick}
    className="flex items-center justify-center space-x-2 w-full py-3 px-4 bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 transition-colors duration-200 shadow-sm"
  >
    {icon}
    <span>{label}</span>
  </button>
);

export default function UserProfiles() {

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [company, setCompany] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [emails, setEmails] = useState(['']); // Start with one empty email field
  const [phoneNumbers, setPhoneNumbers] = useState(['']); // Start with one empty phone field
  const [address, setAddress] = useState('');
  const [month, setMonth] = useState('');
  const [day, setDay] = useState('');
  const [year, setYear] = useState('');

  const handleAddEmail = () => {
    setEmails([...emails, '']);
  };

  const handleEmailChange = (index: number, value: string) => {
    const newEmails = [...emails];
    newEmails[index] = value;
    setEmails(newEmails);
  };

  const handleAddPhoneNumber = () => {
    setPhoneNumbers([...phoneNumbers, '']);
  };

  const handlePhoneNumberChange = (index: number, value: string) => {
    const newPhoneNumbers = [...phoneNumbers];
    newPhoneNumbers[index] = value;
    setPhoneNumbers(newPhoneNumbers);
  };

  // Generate months for dropdown
  const months = [
    "Month", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  // Generate days for dropdown
  const days = ["Day", ...Array.from({ length: 31 }, (_, i) => i + 1)];


  return (
    <>
      <PageMeta
        title="React.js Profile Dashboard | TailAdmin - Next.js Admin Dashboard Template"
        description="This is React.js Profile Dashboard page for TailAdmin - React.js Tailwind CSS Admin Dashboard Template"
      />
      <PageBreadcrumb pageTitle="Profile" />
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] lg:p-6">
        <h3 className="mb-5 text-lg font-semibold text-gray-800 dark:text-white/90 lg:mb-7">
          Profile
        </h3>
        <div className="space-y-6">
         <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-5">
        {/* Profile Picture Section */}
        <div className="flex justify-center mb-6">
          <div className="w-28 h-28 rounded-full bg-blue-100 flex items-center justify-center text-blue-500 text-5xl font-light">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="60"
              height="60"
              viewBox="0 0 24 24"
              fill="currentColor"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="lucide lucide-user"
            >
              <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        </div>

        {/* Name Section */}
        <div className="space-y-4">
          <InputField
            label="First Name"
            placeholder="First name"
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-user"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>}
            value={firstName}
            onChange={(e: { target: { value: React.SetStateAction<string>; }; }) => setFirstName(e.target.value)}
          />
          <InputField
                  label="Last Name"
                  placeholder="Last name"
                  value={lastName}
                  onChange={(e: { target: { value: React.SetStateAction<string>; }; }) => setLastName(e.target.value)}
                  className="ml-8" // Indent as per image
                  icon={undefined}          />
        </div>

        {/* Company Section */}
        <div className="space-y-4">
          <InputField
            label="Company"
            placeholder="Company"
            icon={<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-building"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>}
            value={company}
            onChange={(e: { target: { value: React.SetStateAction<string>; }; }) => setCompany(e.target.value)}
          />
          <InputField
                  label="Job Title"
                  placeholder="Job title"
                  value={jobTitle}
                  onChange={(e: { target: { value: React.SetStateAction<string>; }; }) => setJobTitle(e.target.value)}
                  className="ml-8" // Indent as per image
                  icon={undefined}          />
        </div>

        {/* Email Section */}
        <div className="space-y-4">
          {emails.map((email, index) => (
            <InputField
              key={index}
              label={`Email ${index + 1}`}
              placeholder="Email"
              icon={index === 0 ? <Mail size={20} /> : null}
              type="email"
              value={email}
              onChange={(e: { target: { value: string; }; }) => handleEmailChange(index, e.target.value)}
              className={index > 0 ? "ml-8" : ""}
            />
          ))}
          <AddButton
            label="Add email"
            onClick={handleAddEmail}
            icon={<Plus size={20} />}
          />
        </div>

        {/* Phone Section */}
        <div className="space-y-4">
          {phoneNumbers.map((phone, index) => (
            <div key={index} className="flex items-center space-x-3 bg-white p-3 rounded-md shadow-sm border border-gray-200">
              {index === 0 ? <Phone size={20} className="text-gray-500" /> : <div className="w-5" />} {/* Icon for first phone field */}
              <div className="relative">
                <select
                  className="appearance-none bg-transparent outline-none pr-6 text-gray-800"
                  aria-label="Country Code"
                >
                  <option value="+91">🇮🇳 +91</option>
                  <option value="+1">🇺🇸 +1</option>
                  {/* Add more country codes as needed */}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                  <ChevronDown size={16} />
                </div>
              </div>
              <input
                type="tel"
                placeholder="Phone"
                className="flex-grow outline-none bg-transparent text-gray-800"
                aria-label={`Phone Number ${index + 1}`}
                value={phone}
                onChange={(e) => handlePhoneNumberChange(index, e.target.value)}
              />
            </div>
          ))}
          <AddButton
            label="Add phone"
            onClick={handleAddPhoneNumber}
            icon={<Plus size={20} />}
          />
        </div>

        {/* Address Section */}
        <div className="space-y-4">
          <AddButton
            label="Add address"
            onClick={() => setAddress('Placeholder Address')} // In a real app, this would open a modal/new fields
            icon={<MapPin size={20} />}
          />
          {address && (
            <InputField
                    label="Address"
                    placeholder="Address details"
                    value={address}
                    onChange={(e: { target: { value: React.SetStateAction<string>; }; }) => setAddress(e.target.value)}
                    className="ml-8" icon={undefined}            />
          )}
        </div>

        {/* Significant Date Section */}
        <div className="space-y-4">
          <InputField
                  label="Date Icon"
                  placeholder=""
                  icon={<Calendar size={20} />}
                  className="opacity-0 h-0 p-0 m-0 border-none" // Hidden field just for the icon placement
                  value={undefined} onChange={undefined}          />
          <div className="flex space-x-3 ml-8">
            <div className="relative flex-grow">
              <select
                className="appearance-none w-full bg-white p-3 rounded-md shadow-sm border border-gray-200 outline-none pr-8 text-gray-800"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                aria-label="Month"
              >
                {months.map((m, i) => (
                  <option key={m} value={m === "Month" ? "" : m}>
                    {m}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                <ChevronDown size={16} />
              </div>
            </div>
            <div className="relative w-24">
              <select
                className="appearance-none w-full bg-white p-3 rounded-md shadow-sm border border-gray-200 outline-none pr-8 text-gray-800"
                value={day}
                onChange={(e) => setDay(e.target.value)}
                aria-label="Day"
              >
                {days.map((d) => (
                  <option key={d} value={d === "Day" ? "" : d}>
                    {d}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                <ChevronDown size={16} />
              </div>
            </div>
          </div>
          <InputField
                  label="Year"
                  placeholder="Year (optional)"
                  type="number"
                  value={year}
                  onChange={(e: { target: { value: React.SetStateAction<string>; }; }) => setYear(e.target.value)}
                  className="ml-8" icon={undefined}          />
          <AddButton
            label="Add significant date"
            onClick={() => {}} // No functionality implemented for adding more dates
            icon={<Calendar size={20} />}
          />
        </div>

        {/* Website Section */}
        <AddButton
          label="Add website"
          onClick={() => {}} // No functionality implemented
          icon={<Link size={20} />}
        />

        {/* Related Person Section */}
        <AddButton
          label="Add related person"
          onClick={() => {}} // No functionality implemented
          icon={<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-user-plus"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><path d="M22 11h-4"/><path d="M20 9v4"/></svg>}
        />
      </div>
    </div>
        </div>
      </div>
    </>
  );
}
