import { useEffect, useState } from "react";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import ComponentCard from "../../components/common/ComponentCard";
import Label from "../../components/form/Label";
import { DatePicker, Input, PhoneInput, Select } from "../../components/wrapper";
import { EyeCloseIcon, EyeIcon, PlusIcon, TimeIcon, TrashBinIcon } from "../../icons";
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { contactSchema } from "../../validations/contact";


export default function ContactAdd() {
   const [isSubmitting, setIsSubmitting] = useState(false);

  // Retrieve and validate data from local storage
  const getInitialFormData = (): z.infer<typeof contactSchema> => {

    const storedData = localStorage.getItem("contactFormData");
    if (storedData) {
      console.log("datatatattat",storedData)
      try {
        const parsedData = JSON.parse(storedData);
        const result = contactSchema.safeParse(parsedData);
        if (result.success) {
          return result.data;
        }
      } catch (error) {
        console.error("Failed to parse or validate local storage data:", error);
      }
    }
    return {
      phoneNumbers: [{ type: "", countryCode: "", number: "" }],
      emails: [{ type: "", email: "" }],
      addresses: [{ country: "", state: "", pincode: "", streetAddress: "" }],
      firstName: "",
      lastName: "",
      companyName: "",
      role: "",
    };
  };
  // Define initial default values
  // const initialFormData: z.infer<typeof contactSchema> = {
  //   phoneNumbers: [{ type: "", countryCode: "", number: "" }],
  //   emails: [{ type: "", email: "" }],
  //   addresses: [{ country: "", state: "", pincode: "", streetAddress: "" }],
  //   firstName: "",
  //   lastName: "",
  //   companyName: "",
  //   role: "",
  // };
  // const getInitialFormData = (): z.infer<typeof contactSchema> => {
  //   const storedData = localStorage.getItem("contactFormData");
  //   if (storedData) {
  //     try {
  //       const parsedData = JSON.parse(storedData);
  //       // Merge parsed data with initialFormData to handle partial data
  //       const mergedData: z.infer<typeof contactSchema> = {
  //         ...initialFormData,
  //         ...parsedData,
  //         phoneNumbers: Array.isArray(parsedData.phoneNumbers) && parsedData.phoneNumbers.length > 0
  //           ? parsedData.phoneNumbers.map((phone: any) => ({
  //               type: typeof phone.type === "string" ? phone.type : "",
  //               countryCode: typeof phone.countryCode === "string" ? phone.countryCode : "",
  //               number: typeof phone.number === "string" ? phone.number : "",
  //             }))
  //           : initialFormData.phoneNumbers,
  //         emails: Array.isArray(parsedData.emails) && parsedData.emails.length > 0
  //           ? parsedData.emails.map((email: any) => ({
  //               type: typeof email.type === "string" ? email.type : "",
  //               email: typeof email.email === "string" ? email.email : "",
  //             }))
  //           : initialFormData.emails,
  //         addresses: Array.isArray(parsedData.addresses) && parsedData.addresses.length > 0
  //           ? parsedData.addresses.map((address: any) => ({
  //               country: typeof address.country === "string" ? address.country : "",
  //               state: typeof address.state === "string" ? address.state : "",
  //               pincode: typeof address.pincode === "string" ? address.pincode : "",
  //               streetAddress: typeof address.streetAddress === "string" ? address.streetAddress : "",
  //             }))
  //           : initialFormData.addresses,
  //       };
  //       // Validate merged data
  //       const result = contactSchema.safeParse(mergedData);
  //       if (result.success) {
  //         return result.data;
  //       } else {
  //         console.error("Local storage data validation failed:", result.error);
  //       }
  //     } catch (error) {
  //       console.error("Failed to parse local storage data:", error);
  //     }
  //   }
  //   return initialFormData;
  // };

  const { register, handleSubmit, control, formState: { errors }, watch, reset } = useForm<z.infer<typeof contactSchema>>({
    resolver: zodResolver(contactSchema),
    defaultValues: getInitialFormData(),
  });

  const { fields: phoneFields, append: appendPhone, remove: removePhone } = useFieldArray({
    control,
    name: "phoneNumbers",
  });

  const { fields: emailFields, append: appendEmail, remove: removeEmail } = useFieldArray({
    control,
    name: "emails",
  });

  const { fields: addressFields, append: appendAddress, remove: removeAddress } = useFieldArray({
    control,
    name: "addresses",
  });

  const roleOptions = [
    { value: "SUPER", label: "Superuser" },
    { value: "ADMIN", label: "Administrator" },
    { value: "SALE", label: "Sales" },
    { value: "REP", label: "Representative" },
    { value: "VENDOR", label: "Vendor" },
    { value: "CUSTOMER", label: "Customer" },
    { value: "USER", label: "User" },
    { value: "PUBLIC", label: "Public" },
  ];

  const phoneTypeOptions = [
    { value: "mobile", label: "Mobile" },
    { value: "home", label: "Home" },
    { value: "work", label: "Work" },
    { value: "fax", label: "Fax" },
  ];

  const countryOptions = [
    { value: "IN", label: "India" },
    { value: "BN", label: "Bangladesh" },
    { value: "US", label: "United States" },
    { value: "GB", label: "United Kingdom" },
    { value: "CA", label: "Canada" },
    { value: "AU", label: "Australia" },
  ];

  // Watch all form fields and save to local storage on change
  const formData = watch();
  useEffect(() => {
    try {
      localStorage.setItem("contactFormData", JSON.stringify(formData));
    } catch (error) {
      console.error("Failed to save form data to local storage:", error);
    }
  }, [formData]);

  

  const onSubmit = (data: z.infer<typeof contactSchema>) => {
    console.log("Form Data:", data);
    localStorage.removeItem("contactFormData");
    reset(getInitialFormData);
  };

  return (
    <>
      <PageBreadcrumb pageTitle="Contact Add" />
      <ComponentCard>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="firstName">First Name</Label>
              <Input
                type="text"
                id="firstName"
                placeholder="First Name"
                {...register("firstName")}
              />
              {errors.firstName && (
                <span className="text-red-500 text-sm">
                  {errors.firstName.message}
                </span>
              )}
            </div>
            <div>
              <Label htmlFor="lastName">Last Name</Label>
              <Input
                type="text"
                id="lastName"
                placeholder="Last Name"
                {...register("lastName")}
              />
              {errors.lastName && (
                <span className="text-red-500 text-sm">
                  {errors.lastName.message}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="companyName">Company Name</Label>
              <Input
                type="text"
                id="companyName"
                placeholder="Company"
                {...register("companyName")}
              />
              {errors.companyName && (
                <span className="text-red-500 text-sm">
                  {errors.companyName.message}
                </span>
              )}
            </div>
            <div>
              <Label htmlFor="role">Role</Label>
              <Controller
                name="role"
                control={control}
                render={({ field }) => (
                  <Select
                    options={roleOptions}
                    placeholder="Select an option"
                    value={field.value}
                    onChange={field.onChange}
                    className="dark:bg-dark-900"
                  />
                )}
              />
              {errors.role && (
                <span className="text-red-500 text-sm">
                  {errors.role.message}
                </span>
              )}
            </div>
          </div>

          <div>
            <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
              Phone Numbers
            </Label>
            {phoneFields.map((field, index) => (
              <div key={field.id} className="flex items-end space-x-2 mb-2">
                <div className="w-1/4">
                  <Label htmlFor={`phoneNumbers.${index}.type`}>Type</Label>
                  <Controller
                    name={`phoneNumbers.${index}.type`}
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={phoneTypeOptions}
                        placeholder="Select Type"
                        value={field.value}
                        onChange={field.onChange}
                        className="dark:bg-dark-900"
                      />
                    )}
                  />                 
                   {errors.phoneNumbers?.[index]?.number?.message && (
                    <span className="text-red-500 text-sm">
                      {errors.phoneNumbers[index].number.message}
                    </span>
                  )}
                </div>
                <div className="w-1/6">
                  <Label htmlFor={`phoneNumbers.${index}.countryCode`}>Code</Label>
                  <Input
                    type="text"
                    id={`phoneNumbers.${index}.countryCode`}
                    placeholder="+91"
                    {...register(`phoneNumbers.${index}.countryCode`)}
                  />
                  {errors.phoneNumbers?.[index]?.countryCode && (
                    <span className="text-red-500 text-sm">
                      {errors.phoneNumbers[index].countryCode.message}
                    </span>
                  )}
                </div>
                <div className="flex-1">
                  <Label htmlFor={`phoneNumbers.${index}.number`}>Number</Label>
                  <Input
                    type="text"
                    id={`phoneNumbers.${index}.number`}
                    placeholder="Enter phone number"
                    {...register(`phoneNumbers.${index}.number`)}
                  />
                  {errors.phoneNumbers?.[index]?.number && (
                    <span className="text-red-500 text-sm">
                      {errors.phoneNumbers[index].number.message}
                    </span>
                  )}
                </div>
                {phoneFields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removePhone(index)}
                    className="p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    <TrashBinIcon className="size-5" />
                  </button>
                )}
              </div>
            ))}
            {errors.phoneNumbers && (
              <span className="text-red-500 text-sm">
                {errors.phoneNumbers.message}
              </span>
            )}
            <button
              type="button"
              onClick={() => appendPhone({ type: "", countryCode: "", number: "" })}
              className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              <PlusIcon className="mr-2 size-5" />
              Add Phone Number
            </button>
          </div>

          <div>
            <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
              Email Id
            </Label>
            {emailFields.map((field, index) => (
              <div key={field.id} className="flex items-end space-x-2 mb-2">
                <div className="w-1/4">
                  <Label htmlFor={`emails.${index}.type`}>Type</Label>
                  <Controller
                    name={`emails.${index}.type`}
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={phoneTypeOptions}
                        placeholder="Select Type"
                        value={field.value}
                        onChange={field.onChange}
                        className="dark:bg-dark-900"
                      />
                    )}
                  />   
                  {errors.emails?.[index] && (
                    <span className="text-red-500 text-sm">
                      {errors.emails?.[index]?.message}
                    </span>
                  )}              
                  
                </div>
                <div className="flex-1">
                  <Label htmlFor={`emails.${index}.email`}>Email</Label>
                  <Input
                    type="text"
                    id={`emails.${index}.email`}
                    placeholder="Enter email"
                    {...register(`emails.${index}.email`)}
                  />
                  {errors.emails?.[index]?.email && (
                    <span className="text-red-500 text-sm">
                      {errors.emails[index].email.message}
                    </span>
                  )}
                </div>
                {emailFields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeEmail(index)}
                    className="p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    <TrashBinIcon className="size-5" />
                  </button>
                )}
              </div>
            ))}
            {errors.emails && (
              <span className="text-red-500 text-sm">
                {errors.emails.message}
              </span>
            )}
            <button
              type="button"
              onClick={() => appendEmail({ type: "", email: "" })}
              className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              <PlusIcon className="mr-2 size-5" />
              Add Email
            </button>
          </div>

           <div>
            <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
              Addresses
            </Label>
            {addressFields.map((field, index) => (
              <div key={field.id} className="flex items-end space-x-2 mb-2">
                <div className="w-1/4">
                  <Label htmlFor={`addresses.${index}.country`}>Country</Label>
                  <Controller
                    name={`addresses.${index}.country`}
                    control={control}
                    render={({ field }) => (
                      <Select
                        options={countryOptions}
                        placeholder="Select Country"
                        value={field.value}
                        onChange={field.onChange}
                        className="dark:bg-dark-900"
                      />
                    )}
                  />
                  {errors.addresses?.[index]?.country?.message && (
                    <span className="text-red-500 text-sm">
                      {errors.addresses?.[index]?.country?.message}
                    </span>
                  )}
                </div>
                <div className="w-1/4">
                  <Label htmlFor={`addresses.${index}.state`}>State</Label>
                  <Input
                    type="text"
                    id={`addresses.${index}.state`}
                    placeholder="Enter state"
                    {...register(`addresses.${index}.state`)}
                  />
                  {errors.addresses?.[index]?.state?.message && (
                    <span className="text-red-500 text-sm">
                      {errors.addresses?.[index]?.state?.message}
                    </span>
                  )}
                </div>
                <div className="w-1/6">
                  <Label htmlFor={`addresses.${index}.pincode`}>Pincode</Label>
                  <Input
                    type="text"
                    id={`addresses.${index}.pincode`}
                    placeholder="Enter pincode"
                    {...register(`addresses.${index}.pincode`)}
                  />
                  {errors.addresses?.[index]?.pincode?.message && (
                    <span className="text-red-500 text-sm">
                      {errors.addresses?.[index]?.pincode?.message}
                    </span>
                  )}
                </div>
                <div className="flex-1">
                  <Label htmlFor={`addresses.${index}.streetAddress`}>Street Address</Label>
                  <Input
                    type="text"
                    id={`addresses.${index}.streetAddress`}
                    placeholder="Enter street address"
                    {...register(`addresses.${index}.streetAddress`)}
                  />
                  {errors.addresses?.[index]?.streetAddress?.message && (
                    <span className="text-red-500 text-sm">
                      {errors.addresses?.[index]?.streetAddress?.message}
                    </span>
                  )}
                </div>
                {addressFields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeAddress(index)}
                    className="p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    <TrashBinIcon className="size-5" />
                  </button>
                )}
              </div>
            ))}
            {errors.addresses?.message && (
              <span className="text-red-500 text-sm">
                {errors.addresses.message}
              </span>
            )}
            <button
              type="button"
              onClick={() => appendAddress({ country: "", state: "", pincode: "", streetAddress: "" })}
              className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
            >
              <PlusIcon className="mr-2 size-5" />
              Add Address
            </button>
          </div>

          <button
            type="submit"
            className="flex items-center px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
          >
            Submit
          </button>
        </form>
      </ComponentCard>
    </>
  );
}