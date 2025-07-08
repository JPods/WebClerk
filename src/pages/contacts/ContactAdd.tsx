import { useState } from "react";
import ComponentCard from "../../components/common/ComponentCard";
import Label from "../../components/form/Label";
import {
  DatePicker,
  Input,
  PhoneInput,
  Select,
} from "../../components/wrapper";
import {
  EyeCloseIcon,
  EyeIcon,
  PlusIcon,
  TimeIcon,
  TrashBinIcon,
} from "../../icons";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
// import ComponentCard from "../../common/ComponentCard";
// import Label from "../Label";
// import Input from "../input/InputField";
// import Select from "../Select";
// import { EyeCloseIcon, EyeIcon, TimeIcon } from "../../../icons";
// import DatePicker from "../date-picker.tsx";

export default function ContactAdd() {
  const [showPassword, setShowPassword] = useState(false);
  const options = [
    { value: "marketing", label: "Marketing" },
    { value: "template", label: "Template" },
    { value: "development", label: "Development" },
  ];

   const role = [
    { value: "SUPER", label: "Superuser" },
    { value: "ADMIN", label: "Administrator" },
    { value: "SALE", label: "Sales" },
    { value: "REP", label: "Representative" },
    { value: "VENDOR", label: "Vendor" },
    { value: "CUSTOMER", label: "Customer" },
    { value: "USER", label: "User" },
    { value: "PUBLIC", label: "Public" },
  ];
  const handleSelectChange = (value: string) => {
    console.log("Selected value:", value);
  };

  const countries = [
    { code: "US", label: "+1" },
    { code: "GB", label: "+44" },
    { code: "CA", label: "+1" },
    { code: "AU", label: "+61" },
  ];
  //   const handlePhoneNumberChange = (phoneNumber: string) => {
  //     console.log("Updated phone number:", phoneNumber);
  //   };

  const [phoneNumbers, setPhoneNumbers] = useState([
    { id: 1, type: "", countryCode: "", number: "" }, // Initial row
  ]);
  
  const [email, setEmail] = useState([
    { id: 1, type: "", email: "" }, // Initial row
  ]);

  const phoneTypeOptions = [
    { value: "mobile", label: "Mobile" },
    { value: "home", label: "Home" },
    { value: "work", label: "Work" },
    { value: "fax", label: "Fax" },
  ];

  // Phone multiple
  const handlePhoneNumberChange = (
    id: number,
    field: string,
    value: string
  ) => {
    setPhoneNumbers((prevNumbers) =>
      prevNumbers.map((phone) =>
        phone.id === id ? { ...phone, [field]: value } : phone
      )
    );
  };

  const addPhoneNumberRow = () => {
    setPhoneNumbers((prevNumbers) => [
      ...prevNumbers,
      { id: Date.now(), type: "", countryCode: "", number: "" }, // Use Date.now() for a unique ID
    ]);
  };

  const removePhoneNumberRow = (id: number) => {
    setPhoneNumbers((prevNumbers) =>
      prevNumbers.filter((phone) => phone.id !== id)
    );
  };

  // Email multiple

  const handleEmailChange = (
    id: number,
    field: string,
    value: string
  ) => {
    setEmail((prevNumbers) =>
      prevNumbers.map((mail) =>
        mail.id === id ? { ...mail, [field]: value } : mail
      )
    );
  };

  const addEmailRow = () => {
    setEmail((prevNumbers) => [
      ...prevNumbers,
      { id: Date.now(), type: "", email: "" }, // Use Date.now() for a unique ID
    ]);
  };

  const removeEmailRow = (id: number) => {
    setEmail((prevNumbers) =>
      prevNumbers.filter((mail) => mail.id !== id)
    );
  };

  return (
    <>
      <PageBreadcrumb pageTitle="Contact Add" />
      <ComponentCard>
        <div className="space-y-6">

           <div className="grid grid-cols-2 gap-4">
                <div>
                    <Label htmlFor="inputTwo">First Name</Label>
                    <Input type="text" id="inputTwo" placeholder="First Name" />
                </div>
                <div>
                    <Label htmlFor="inputTwo">Last Name</Label>
                    <Input type="text" id="inputTwo" placeholder="Last Name" />
                </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
                <div>
                    <Label htmlFor="inputTwo">Company Name</Label>
                    <Input type="text" id="inputTwo" placeholder="Company" />
                </div>
                <div>
                    <Label htmlFor="inputTwo">Role</Label>
                   <Select
                    options={role}
                    placeholder="Select an option"
                    onChange={handleSelectChange}
                    className="dark:bg-dark-900"
                    value={""}
                    />
                </div>
          </div>

          <div>
            <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
              Phone Numbers
            </Label>
            {phoneNumbers.map((phone, index) => (
              <div key={phone.id} className="flex items-end space-x-2">
                {/* Phone Type Select */}
                <div className="w-1/4">
                  <Label htmlFor={`phoneType-${phone.id}`}>Type</Label>
                  <Select
                    //id={`phoneType-${phone.id}`}
                    options={phoneTypeOptions}
                    placeholder="Select Type"
                    value={phone.type}
                    onChange={(selectedOption) =>
                      handlePhoneNumberChange(phone.id, "type", selectedOption)
                    }
                    className="dark:bg-dark-900"
                  />
                </div>

                {/* Country Code Input */}
                <div className="w-1/6">
                  <Label htmlFor={`countryCode-${phone.id}`}>Code</Label>
                  <Input
                    type="text"
                    id={`countryCode-${phone.id}`}
                    placeholder="+91"
                    value={phone.countryCode}
                    onChange={(e) =>
                      handlePhoneNumberChange(
                        phone.id,
                        "countryCode",
                        e.target.value
                      )
                    }
                  />
                </div>

                {/* Mobile Number Input */}
                <div className="flex-1">
                  <Label htmlFor={`phoneNumber-${phone.id}`}>Number</Label>
                  <Input
                    type="text"
                    id={`phoneNumber-${phone.id}`}
                    placeholder="Enter mobile number"
                    value={phone.number}
                    onChange={(e) =>
                      handlePhoneNumberChange(
                        phone.id,
                        "number",
                        e.target.value
                      )
                    }
                  />
                </div>

                {/* Remove Button */}
                {phoneNumbers.length > 1 && ( // Only show remove if more than one row
                  <button
                    type="button"
                    onClick={() => removePhoneNumberRow(phone.id)}
                    className="p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    {/* Assuming Trash2 is your remove icon component */}
                    <TrashBinIcon className="size-5" />
                  </button>
                )}
              </div>
            ))}

            {/* Add New Row Button */}
            <button
              type="button"
              onClick={addPhoneNumberRow}
              className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              {/* Assuming Plus is your add icon component */}
              <PlusIcon className="mr-2 size-5" /> Add Phone Number
            </button>
          </div>
          
          <div>
                <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
                Email Id
                </Label>
                {email.map((mail, index) => (
                <div key={mail.id} className="flex items-end space-x-2">
                    {/* Phone Type Select */}
                    <div className="w-1/4">
                    <Label htmlFor={`phoneType-${mail.id}`}>Type</Label>
                    <Select
                        //id={`phoneType-${mail.id}`}
                        options={phoneTypeOptions}
                        placeholder="Select Type"
                        value={mail.type}
                        onChange={(selectedOption) =>
                        handlePhoneNumberChange(mail.id, "type", selectedOption)
                        }
                        className="dark:bg-dark-900"
                    />
                    </div>

                    {/* Mobile Number Input */}
                    <div className="flex-1">
                    <Label htmlFor={`email-${mail.id}`}>Email</Label>
                    <Input
                        type="text"
                        id={`email-${mail.id}`}
                        placeholder="Enter mobile number"
                        value={mail.email}
                        onChange={(e) =>
                        handleEmailChange(
                            mail.id,
                            "email",
                            e.target.value
                        )
                        }
                    />
                    </div>

                    {/* Remove Button */}
                    {email.length > 1 && ( // Only show remove if more than one row
                    <button
                        type="button"
                        onClick={() => removeEmailRow(mail.id)}
                        className="p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                        {/* Assuming Trash2 is your remove icon component */}
                        <TrashBinIcon className="size-5" />
                    </button>
                    )}
                </div>
                ))}

                {/* Add New Row Button */}
                <button
                type="button"
                onClick={addEmailRow}
                className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
                >
                {/* Assuming Plus is your add icon component */}
                <PlusIcon className="mr-2 size-5" /> Add Email
                </button>
          </div>

          <div>
            <Label htmlFor="inputTwo">Input with Placeholder</Label>
            <Input type="text" id="inputTwo" placeholder="info@gmail.com" />
          </div>
          <div>
            <Label>Select Input</Label>
            <Select
              options={options}
              placeholder="Select an option"
              onChange={handleSelectChange}
              className="dark:bg-dark-900"
              value={""}
            />
          </div>
          <div>
            <Label>Phone</Label>
            <PhoneInput
              selectPosition="start"
              countries={countries}
              placeholder="+1 (555) 000-0000"
              onChange={() => handlePhoneNumberChange}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Password Input</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                />
                <button
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                >
                  {showPassword ? (
                    <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                  ) : (
                    <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                  )}
                </button>
              </div>
            </div>
            <div>
              <DatePicker
                id="date-picker"
                label="Date Picker Input"
                placeholder="Select a date"
                onChange={(dates, currentDateString) => {
                  // Handle your logic
                  console.log({ dates, currentDateString });
                }}
              />
            </div>
          </div>
          <div>
            <Label htmlFor="tm">Time Picker Input</Label>
            <div className="relative">
              <Input
                type="time"
                id="tm"
                name="tm"
                onChange={(e) => console.log(e.target.value)}
              />
              <span className="absolute text-gray-500 -translate-y-1/2 pointer-events-none right-3 top-1/2 dark:text-gray-400">
                <TimeIcon className="size-6" />
              </span>
            </div>
          </div>
          <div>
            <Label htmlFor="tm">Input with Payment</Label>
            <div className="relative">
              <Input
                type="text"
                placeholder="Card number"
                className="pl-[62px]"
              />
              <span className="absolute left-0 top-1/2 flex h-11 w-[46px] -translate-y-1/2 items-center justify-center border-r border-gray-200 dark:border-gray-800">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle cx="6.25" cy="10" r="5.625" fill="#E80B26" />
                  <circle cx="13.75" cy="10" r="5.625" fill="#F59D31" />
                  <path
                    d="M10 14.1924C11.1508 13.1625 11.875 11.6657 11.875 9.99979C11.875 8.33383 11.1508 6.8371 10 5.80713C8.84918 6.8371 8.125 8.33383 8.125 9.99979C8.125 11.6657 8.84918 13.1625 10 14.1924Z"
                    fill="#FC6020"
                  />
                </svg>
              </span>
            </div>
          </div>
        </div>
      </ComponentCard>
    </>
  );
}
