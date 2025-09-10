import { useModal } from "../../hooks/useModal";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";
import Label from "../form/Label";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import z from "zod";
import { addressSchema } from "../../validations/contact";
import { PlusIcon, TrashBinIcon } from "../../icons";
import { Select } from "../wrapper";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { getAddress, getDomain, postAddress, postDomain } from "../../api/userProfile";
import { useEffect } from "react";

export default function UserAddressCard() {
  const { isOpen, openModal, closeModal } = useModal();
  const handleSave = () => {
    // Handle save logic here
    console.log("Saving changes...");
    closeModal();
  };
  
  const dispatch = useDispatch()

  const { register, handleSubmit, control, formState: { errors }, setValue, getValues, watch, reset } = useForm<z.infer<typeof addressSchema>>({
      resolver: zodResolver(addressSchema),
      defaultValues:{
        addresses: [{ country: "", state: "", zip: "", address1: "" }],
        domains: [{ path: "", type: "", comment: "" }]
      },
    });

  const { fields: addressFields, append: appendAddress, remove: removeAddress } = useFieldArray({
      control,
      name: "addresses",
    });

  const { fields: domainFields, append: appendDomain, remove: removeDomain } = useFieldArray({
      control,
      name: "domains",
    });

    const countryOptions = [
    { value: "IN", label: "India" },
    { value: "BN", label: "Bangladesh" },
    { value: "US", label: "United States" },
    { value: "GB", label: "United Kingdom" },
    { value: "CA", label: "Canada" },
    { value: "AU", label: "Australia" },
  ];

  useEffect(() => {      
        getAddresses()
        getDomains()
    },[])
    
     const getAddresses = async() => {
        try {         
          const res = await getAddress()       
          setValue('addresses',res)
        } catch (error) {
          
        }
    }
  
     const getDomains = async() => {
        try {         
          const res = await getDomain()       
          setValue('domains', res)
    
        } catch (error) {
          
        }
    }

   const onSubmit = async(data: any) => {
     
     try {
         const [addressResponse, domainResponse] = await Promise.all([
                      Promise.all(data.addresses.map((list: any) => postAddress(list))),
                      Promise.all(data.domains.map((list: any) => postDomain(list))),
                   ]);                   
                  dispatch(showToast({ message: "Profile addresses uploaded successfully", type: "success" }));
     } catch (error:any) {
          dispatch(showToast({ message: error.message, type: "error" }));
     }

      // localStorage.removeItem("contactFormData");
      // reset();
    };

  return (
    <>
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h4 className="text-lg font-semibold text-gray-800 dark:text-white/90 lg:mb-6">
              Addresses & Domains
            </h4>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-7 2xl:gap-x-32">
              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  Country
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  United States.
                </p>
              </div>

              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  City/State
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  Phoenix, Arizona, United States.
                </p>
              </div>

              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  Postal Code
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  ERT 2489
                </p>
              </div>

              <div>
                <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                  TAX ID
                </p>
                <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                  AS4568384
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={openModal}
            className="flex w-full items-center justify-center gap-2 rounded-full border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200 lg:inline-flex lg:w-auto"
          >
            <svg
              className="fill-current"
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M15.0911 2.78206C14.2125 1.90338 12.7878 1.90338 11.9092 2.78206L4.57524 10.116C4.26682 10.4244 4.0547 10.8158 3.96468 11.2426L3.31231 14.3352C3.25997 14.5833 3.33653 14.841 3.51583 15.0203C3.69512 15.1996 3.95286 15.2761 4.20096 15.2238L7.29355 14.5714C7.72031 14.4814 8.11172 14.2693 8.42013 13.9609L15.7541 6.62695C16.6327 5.74827 16.6327 4.32365 15.7541 3.44497L15.0911 2.78206ZM12.9698 3.84272C13.2627 3.54982 13.7376 3.54982 14.0305 3.84272L14.6934 4.50563C14.9863 4.79852 14.9863 5.2734 14.6934 5.56629L14.044 6.21573L12.3204 4.49215L12.9698 3.84272ZM11.2597 5.55281L5.6359 11.1766C5.53309 11.2794 5.46238 11.4099 5.43238 11.5522L5.01758 13.5185L6.98394 13.1037C7.1262 13.0737 7.25666 13.003 7.35947 12.9002L12.9833 7.27639L11.2597 5.55281Z"
                fill=""
              />
            </svg>
            Edit
          </button>
        </div>
      </div>
      <Modal isOpen={isOpen} onClose={closeModal} className="max-w-[700px] m-4">
        <div className="relative w-full p-4 overflow-y-auto bg-white no-scrollbar rounded-3xl dark:bg-gray-900 lg:p-11">
          <div className="px-2 pr-14">
            <h4 className="mb-2 text-2xl font-semibold text-gray-800 dark:text-white/90">
              Edit Address and Domains
            </h4>
            <p className="mb-6 text-sm text-gray-500 dark:text-gray-400 lg:mb-7">
              Update your details to keep your profile up-to-date.
            </p>
          </div>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col">
            <div className="px-2 overflow-y-auto custom-scrollbar">
              <div className="grid grid-cols-1 gap-x-6 gap-y-5 mb-4">
                 <div>
                      <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
                        Addresses
                      </Label>
                      {addressFields.map((field, index) => (
                        <div key={field.id} className="grid grid-cols-1 xl:grid-cols-3 gap-x-6 gap-y-5 mb-4 p-2 border border-gray-200 dark:border-amber-500 rounded-xl">
                          <div className="w-full ml-2">
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
                          <div className="w-full">
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
                          <div className="w-full">
                            <Label htmlFor={`addresses.${index}.zip`}>Zipcode</Label>
                            <Input
                              type="text"
                              id={`addresses.${index}.zip`}
                              placeholder="Enter zip"
                              {...register(`addresses.${index}.zip`)}
                              className="mr-3"
                            />
                            {errors.addresses?.[index]?.zip?.message && (
                              <span className="text-red-500 text-sm">
                                {errors.addresses?.[index]?.zip?.message}
                              </span>
                            )}
                          </div>
                          <div className="w-full ml-2 mb-2">
                            <Label htmlFor={`addresses.${index}.address1`}>Street Address</Label>
                            <Input
                              type="text"
                              id={`addresses.${index}.address1`}
                              placeholder="Enter street address"
                              {...register(`addresses.${index}.address1`)}
                            />
                            {errors.addresses?.[index]?.address1?.message && (
                              <span className="text-red-500 text-sm">
                                {errors.addresses?.[index]?.address1?.message}
                              </span>
                            )}
                          </div>
                          {addressFields.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeAddress(index)}
                              className="mt-6 p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
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
                        onClick={() => appendAddress({ country: "", state: "", zip: "", address1: "" })}
                        className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
                      >
                        <PlusIcon className="mr-2 size-5" />
                        Add Address
                      </button>
                  </div>
              </div>
              <div className="grid grid-cols-1 gap-x-6 gap-y-5">
                 <div>
                      <Label className="block text-base font-medium text-gray-700 dark:text-gray-300">
                        Domains
                      </Label>
                      {domainFields.map((field, index) => (
                        <div key={field.id} className="grid grid-cols-1 xl:grid-cols-2 gap-x-6 gap-y-5 mb-4 p-2 border border-gray-200 dark:border-pink-500 rounded-xl">
                          
                          <div className="w-full">
                            <Label htmlFor={`domains.${index}.state`}>Path</Label>
                            <Input
                              type="text"
                              id={`domains.${index}.path`}
                              placeholder="Enter state"
                              {...register(`domains.${index}.path`)}
                            />
                            {errors.domains?.[index]?.path?.message && (
                              <span className="text-red-500 text-sm">
                                {errors.domains?.[index]?.path?.message}
                              </span>
                            )}
                          </div>
                          <div className="w-full">
                            <Label htmlFor={`domains.${index}.type`}>Type</Label>
                            <Input
                              type="text"
                              id={`domains.${index}.type`}
                              placeholder="Enter type"
                              {...register(`domains.${index}.type`)}
                              className="mr-3"
                            />
                            {errors.domains?.[index]?.message && (
                              <span className="text-red-500 text-sm">
                                {errors.domains?.[index]?.message}
                              </span>
                            )}
                          </div>
                          <div className="w-full ml-2 mb-2">
                            <Label htmlFor={`domains.${index}.comment`}>Comments</Label>
                            <Input
                              type="text"
                              id={`domains.${index}.comment`}
                              placeholder="Enter street address"
                              {...register(`domains.${index}.comment`)}
                            />
                            {errors.domains?.[index]?.comment?.message && (
                              <span className="text-red-500 text-sm">
                                {errors.domains?.[index]?.comment?.message}
                              </span>
                            )}
                          </div>
                          {domainFields.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeDomain(index)}
                              className="mt-6 p-2 text-red-500 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
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
                        onClick={() => appendDomain({ path: "", type: "", comment: "" })}
                        className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
                      >
                        <PlusIcon className="mr-2 size-5" />
                        Add Domain
                      </button>
                  </div>
              </div>
            </div>
            <div className="flex items-center gap-3 px-2 mt-6 lg:justify-end">
              <Button size="sm" variant="outline" onClick={closeModal}>
                Close
              </Button>
              <Button type="submit" size="sm">
                Save Changes
              </Button>
            </div>
          </form>
        </div>
      </Modal>
    </>
  );
}
