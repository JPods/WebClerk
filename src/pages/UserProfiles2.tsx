import React, { useState } from 'react';

// --- Basic UI Components (Self-contained for this example) ---
// These components are styled with Tailwind CSS to match common UI patterns.

const Label: React.FC<{ children: React.ReactNode; htmlFor?: string }> = ({ children, htmlFor }) => (
  <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700 dark:text-white/80 mb-1">
    {children}
  </label>
);

const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement>> = (props) => (
  <input
    {...props}
    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white p-2"
  />
);

const TextArea: React.FC<React.TextareaHTMLAttributes<HTMLTextAreaElement>> = (props) => (
  <textarea
    {...props}
    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white p-2 min-h-[60px]"
  />
);

const Button: React.FC<React.ButtonHTMLAttributes<HTMLButtonElement>> = ({ children, className, ...props }) => (
  <button
    {...props}
    className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-indigo-700 dark:hover:bg-indigo-800 transition-colors ${className}`}
  >
    {children}
  </button>
);

const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement>> = (props) => (
  <select
    {...props}
    className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white p-2"
  />
);

// --- Type Definitions ---
interface ContactItem {
  id: string; // Unique ID for keying in lists
  label: string;
  value: string; // For email address or phone number
  countryCode?: string; // Only for phone numbers
}

interface CountryCodeOption {
  code: string;
  name: string;
}

interface AddressItem {
  id: string;
  country: string;
  state: string;
  zipCode: string;
  streetAddress: string;
}

// --- Data for Select Dropdowns ---
const phoneLabels: string[] = ['Office', 'Home', 'Mobile', 'Main'];
const emailLabels: string[] = ['Office', 'Personal', 'Work', 'Main'];
const countryCodes: CountryCodeOption[] = [
  { code: '+1', name: 'USA' },
  { code: '+44', name: 'UK' },
  { code: '+91', name: 'India' },
  { code: '+61', name: 'Australia' },
  { code: '+49', name: 'Germany' },
  { code: '+33', name: 'France' },
  { code: '+81', name: 'Japan' },
  { code: '+86', name: 'China' },
  { code: '+55', name: 'Brazil' },
  { code: '+27', name: 'South Africa' },
  // Add more country codes as needed
];

const countries: string[] = ['USA', 'Canada', 'UK', 'India', 'Australia'];
const states: { [key: string]: string[] } = {
  USA: ['California', 'New York', 'Texas', 'Florida'],
  Canada: ['Ontario', 'Quebec', 'British Columbia'],
  UK: ['England', 'Scotland', 'Wales'],
  India: ['Maharashtra', 'Karnataka', 'Tamil Nadu', 'West Bengal'],
  Australia: ['New South Wales', 'Victoria', 'Queensland']
};

// --- Main Edit Contact Form Component ---
const App: React.FC = () => {
  // State for basic contact information
  const [lastName, setLastName] = useState<string>('Karar');
  const [firstName, setFirstName] = useState<string>('Riju');
  const [miscellaneous, setMiscellaneous] = useState<string>('Enter your miscellaneous');
  const [miscCharCount, setMiscCharCount] = useState<number>(miscellaneous.length);
  const MAX_MISC_CHARS = 250; // Increased for example, image shows 16 but likely a placeholder

  // State for dynamic email addresses
  const [emails, setEmails] = useState<ContactItem[]>([
    { id: 'email-1', label: 'Office', value: 'tims@dialmycalls.com' },
    { id: 'email-2', label: 'Main', value: 'tsmith@ontimetelecom.com' },
  ]);

  // State for dynamic phone numbers
  const [phoneNumbers, setPhoneNumbers] = useState<ContactItem[]>([
    { id: 'phone-1', label: 'Office', countryCode: '+1', value: '(800) 928-2086' },
    { id: 'phone-2', label: 'Main', countryCode: '+1', value: '(561) 536-4803' },
  ]);

  // State for dynamic addresses
  const [addresses, setAddresses] = useState<AddressItem[]>([
    { id: 'address-1', country: 'USA', state: 'California', zipCode: '90210', streetAddress: '123 Main St' }
  ]);

  /**
   * Generates a unique ID for new contact items.
   * In a real app, you might use a UUID library.
   */
  const generateUniqueId = (): string => {
    return Math.random().toString(36).substr(2, 9);
  };

  // --- Email Handlers ---
  const handleAddEmail = () => {
    setEmails([...emails, { id: generateUniqueId(), label: emailLabels[0], value: '' }]);
  };

  const handleUpdateEmail = (id: string, field: 'label' | 'value', value: string) => {
    setEmails(
      emails.map((email) => (email.id === id ? { ...email, [field]: value } : email))
    );
  };

  const handleRemoveEmail = (id: string) => {
    setEmails(emails.filter((email) => email.id !== id));
  };

  // --- Phone Handlers ---
  const handleAddPhoneNumber = () => {
    setPhoneNumbers([...phoneNumbers, { id: generateUniqueId(), label: phoneLabels[0], countryCode: countryCodes[0].code, value: '' }]);
  };

  const handleUpdatePhoneNumber = (id: string, field: 'label' | 'countryCode' | 'value', value: string) => {
    setPhoneNumbers(
      phoneNumbers.map((phone) => (phone.id === id ? { ...phone, [field]: value } : phone))
    );
  };

  const handleRemovePhoneNumber = (id: string) => {
    setPhoneNumbers(phoneNumbers.filter((phone) => phone.id !== id));
  };

  // --- Address Handlers ---
  const handleAddAddress = () => {
    setAddresses([...addresses, { id: generateUniqueId(), country: countries[0], state: states[countries[0]]?.[0] || '', zipCode: '', streetAddress: '' }]);
  };

  const handleUpdateAddress = (id: string, field: keyof AddressItem, value: string) => {
    setAddresses(
      addresses.map((address) => (address.id === id ? { ...address, [field]: value } : address))
    );
  };

  const handleRemoveAddress = (id: string) => {
    setAddresses(addresses.filter((address) => address.id !== id));
  };

  const handleMiscellaneousChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    if (text.length <= MAX_MISC_CHARS) {
      setMiscellaneous(text);
      setMiscCharCount(text.length);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f5f5] flex items-center justify-center p-4">
      {/* Modal / Card Container */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl overflow-hidden">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Edit Contact</h2>
          <button
            onClick={() => console.log('Close modal')} // Placeholder for closing logic
            className="text-gray-400 hover:text-gray-600 dark:text-gray-300 dark:hover:text-gray-500"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="1.5"
              stroke="currentColor"
              className="w-6 h-6"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6 space-y-5">
          {/* First Name */}
          <div>
            <Label htmlFor="firstName">First Name</Label>
            <Input
              id="firstName"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>

          {/* Last Name */}
          <div>
            <Label htmlFor="lastName">Last Name</Label>
            <Input
              id="lastName"
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
          
          {/* Miscellaneous */}
          <div>
            <Label htmlFor="miscellaneous">Miscellaneous</Label>
            <TextArea
              id="miscellaneous"
              value={miscellaneous}
              onChange={handleMiscellaneousChange}
              maxLength={MAX_MISC_CHARS}
            />
            <p className="text-right text-xs text-gray-500 dark:text-gray-400 mt-1">
              Characters Available: {MAX_MISC_CHARS - miscCharCount}
            </p>
          </div>

          {/* Phone Numbers Section */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h5 className="text-base font-medium text-gray-800 dark:text-white mb-3">
              Phone Numbers <span className="text-sm text-gray-500">(required)</span>
            </h5>
            {phoneNumbers.map((phone) => (
              <div key={phone.id} className="flex flex-col sm:flex-row items-center gap-2 mb-3">
                <Select
                  value={phone.label}
                  onChange={(e) => handleUpdatePhoneNumber(phone.id, 'label', e.target.value)}
                  className="w-full sm:w-1/4"
                >
                  {phoneLabels.map((label) => (
                    <option key={label} value={label}>{label}</option>
                  ))}
                </Select>
                <Select
                  value={phone.countryCode}
                  onChange={(e) => handleUpdatePhoneNumber(phone.id, 'countryCode', e.target.value)}
                  className="w-full sm:w-1/5" // Adjust width for flag/code dropdown
                >
                  {countryCodes.map((cc) => (
                    <option key={cc.code} value={cc.code}>
                      {cc.code} {cc.name}
                    </option>
                  ))}
                </Select>
                <Input
                  type="text"
                  value={phone.value}
                  onChange={(e) => handleUpdatePhoneNumber(phone.id, 'value', e.target.value)}
                  placeholder="Enter phone number"
                  className="flex-grow w-full sm:w-auto mt-2 sm:mt-0"
                />
                {phoneNumbers.length > 1 && (
                  <Button
                    type="button"
                    onClick={() => handleRemovePhoneNumber(phone.id)}
                    className="bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 px-2 py-1 text-xs ml-2 mt-2 sm:mt-0" // Small button styling
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button type="button" onClick={handleAddPhoneNumber} className="mt-3">
              + Add Phone Number
            </Button>
          </div>

          {/* E-mail Addresses Section */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h5 className="text-base font-medium text-gray-800 dark:text-white mb-3">
              E-mail Addresses
            </h5>
            {emails.map((email) => (
              <div key={email.id} className="flex flex-col sm:flex-row items-center gap-2 mb-3">
                <Select
                  value={email.label}
                  onChange={(e) => handleUpdateEmail(email.id, 'label', e.target.value)}
                  className="w-full sm:w-1/4"
                >
                  {emailLabels.map((label) => (
                    <option key={label} value={label}>{label}</option>
                  ))}
                </Select>
                <Input
                  type="email"
                  value={email.value}
                  onChange={(e) => handleUpdateEmail(email.id, 'value', e.target.value)}
                  placeholder="Enter email address"
                  className="flex-grow w-full sm:w-auto mt-2 sm:mt-0"
                />
                 {emails.length > 1 && (
                  <Button
                    type="button"
                    onClick={() => handleRemoveEmail(email.id)}
                    className="bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 px-2 py-1 text-xs ml-2 mt-2 sm:mt-0" // Small button styling
                  >
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button type="button" onClick={handleAddEmail} className="mt-3">
              + Add E-mail Address
            </Button>
          </div>

          {/* Addresses Section */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <h5 className="text-base font-medium text-gray-800 dark:text-white mb-3">
              Addresses
            </h5>
            {addresses.map((address) => (
              <div key={address.id} className="flex flex-col gap-2 mb-4 p-3 border border-gray-200 dark:border-gray-700 rounded-md">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {/* Country */}
                  <div>
                    <Label htmlFor={`country-${address.id}`}>Country</Label>
                    <Select
                      id={`country-${address.id}`}
                      value={address.country}
                      onChange={(e) => handleUpdateAddress(address.id, 'country', e.target.value)}
                      className="w-full"
                    >
                      {countries.map((country) => (
                        <option key={country} value={country}>{country}</option>
                      ))}
                    </Select>
                  </div>
                  {/* State */}
                  <div>
                    <Label htmlFor={`state-${address.id}`}>State</Label>
                    <Select
                      id={`state-${address.id}`}
                      value={address.state}
                      onChange={(e) => handleUpdateAddress(address.id, 'state', e.target.value)}
                      className="w-full"
                    >
                      {states[address.country]?.map((state) => (
                        <option key={state} value={state}>{state}</option>
                      )) || <option value="">Select a country first</option>}
                    </Select>
                  </div>
                  {/* Zip Code */}
                  <div className="col-span-2"> {/* Takes full width on small screens */}
                    <Label htmlFor={`zipCode-${address.id}`}>Zip Code</Label>
                    <Input
                      id={`zipCode-${address.id}`}
                      type="text"
                      value={address.zipCode}
                      onChange={(e) => handleUpdateAddress(address.id, 'zipCode', e.target.value)}
                      placeholder="Enter zip code"
                    />
                  </div>
                  {/* Street Address */}
                  <div className="col-span-2"> {/* Takes full width on small screens */}
                    <Label htmlFor={`streetAddress-${address.id}`}>Street Address</Label>
                    <Input
                      id={`streetAddress-${address.id}`}
                      type="text"
                      value={address.streetAddress}
                      onChange={(e) => handleUpdateAddress(address.id, 'streetAddress', e.target.value)}
                      placeholder="Enter street address"
                    />
                  </div>
                </div>
                {addresses.length > 1 && (
                  <Button
                    type="button"
                    onClick={() => handleRemoveAddress(address.id)}
                    className="bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 px-2 py-1 text-xs self-end mt-2" // Small button styling, aligned to end
                  >
                    Remove Address
                  </Button>
                )}
              </div>
            ))}
            <Button type="button" onClick={handleAddAddress} className="mt-3">
              + Add Address
            </Button>
          </div>         

          {/* Add To Do Not Contact */}
          <div className="flex items-center pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" className="bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 mr-1">
                <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94l-1.72-1.72z" />
              </svg>
              Add To Do Not Contact
            </Button>
          </div>
        </div>

        {/* Footer Buttons */}
        <div className="flex justify-end p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700 space-x-3">
          <Button
            type="button"
            onClick={() => console.log('Close')} // Placeholder for close logic
            className="bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-600 dark:text-white dark:hover:bg-gray-500"
          >
            Close
          </Button>
          <Button
            type="button"
            onClick={() => console.log('Save & Close')} // Placeholder for save logic
            className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800"
          >
            Save & Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default App;
