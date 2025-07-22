import { useModal } from "../../hooks/useModal";
import { Modal } from "../ui/modal";
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";
import Label from "../form/Label";
import { useAppSelector } from "../../store/hooks";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { contactSchema } from "../../validations/contact";
import { zodResolver } from "@hookform/resolvers/zod";
import z from "zod";
import { PlusIcon, TrashBinIcon } from "../../icons";
import { Select } from "../wrapper";
import { getAddress, getEmail, getPhone, patchUserProfile, postEmail, postPhone } from "../../api/userProfile";
import { showToast } from "../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useEffect, useState } from "react";
import { dynamicData } from "../../model/dynamicData";

const phoneTypeOptions = [
    { value: "mobile", label: "Mobile" },
    { value: "home", label: "Home" },
    { value: "work", label: "Work" },
    { value: "fax", label: "Fax" },
  ];

export default function UserInfoCard() {
  const { isOpen, openModal, closeModal } = useModal();
   const { user } = useAppSelector((state) => state.auth);
   const dispatch = useDispatch()
   
  const handleSave = () => {
    // Handle save logic here
    console.log("Saving changes...");
    closeModal();
  };
  
  useEffect(() => {
      getAddressData()
      getPhones()
      getEmails()
  },[])
  
   const getPhones = async() => {
      try {         
        const res = await getPhone()       
        setValue('phoneNumbers',res.filter((list:any) => list.number !== ''))
      } catch (error) {
        
      }
  }

   const getEmails = async() => {
      try {         
        const res = await getEmail()       
        setValue('emails', res)
  
      } catch (error) {
        
      }
  }

  const getAddressData = () => {
      try {         
        const res = getAddress(user?.id)
        console.log("address data", res)
      } catch (error) {
        
      }
  }

  const { register, handleSubmit, control, formState: { errors }, setValue, getValues, reset } = useForm<z.infer<typeof contactSchema>>({
      resolver: zodResolver(contactSchema),
      defaultValues: { 
         name_first: user ? user.name_first : '',
         name_middle: user ? user.name_middle : '',
         name_last: user ? user.name_last : '',         
         phoneNumbers: [{ format: "", country_code: "", number: "" }],    
         emails: [{ type: "", email: "" }],  
      },
    });

    useEffect(() => {
      console.log("user", user)
         setValue('company', user ? user.company: '');
    },[])
    
   const { fields: phoneFields, append: appendPhone, remove: removePhone } = useFieldArray({
       control,
       name: "phoneNumbers",
     });

    const { fields: emailFields, append: appendEmail, remove: removeEmail } = useFieldArray({
      control,
      name: "emails",
    });

   const onSubmit = async(data: any) => {
      const {name_first, name_last, name_middle, company} = data
      const userProfile = {name_first,name_last,name_middle,company}
      try {
           const [userResponse, phoneResponses, emailResponse] = await Promise.all([
              patchUserProfile(userProfile),
              Promise.all(data.phoneNumbers.map((list: any) => postPhone(list))),
              Promise.all(data.emails.map((list: any) => postEmail(list))),
           ]);
           
           if(userResponse.status === 200)
              dispatch(showToast({ message: "Profile Updated successfully", type: "success" }));
           
          console.log("response", phoneResponses, emailResponse)
      } catch (error) {
           dispatch(showToast({ message: " Error on form submit", type: "error" }));
      }
      //localStorage.removeItem("contactFormData");
      //reset(getInitialFormData);
    };
    
    console.log("errors", errors)
    
  return (
    <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h4 className="text-lg font-semibold text-gray-800 dark:text-white/90 lg:mb-6">
            Personal Information
          </h4>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-7 2xl:gap-x-32">
            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                First Name
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user !== null ? user.name_first : "User" }
              </p>
            </div>
            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Middle Name
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user !== null ? user.name_middle : "" }
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Last Name
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user !== null ? user.name_last : "" }
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Email address
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user && user.email }
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Phone
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                {getValues('phoneNumbers').filter((list:any) => list.number !== '').map((list: any) => list.number !== '' && list.number)[0]}
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Role
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user !== null ? user.role : 'User' }
              </p>
            </div>

            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Company
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user && user.company }
              </p>
            </div>
            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                Joining Date
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user && user.date_joined }
              </p>
            </div>
            <div>
              <p className="mb-2 text-xs leading-normal text-gray-500 dark:text-gray-400">
                rank
              </p>
              <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                { user && user.rank }
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

      <Modal isOpen={isOpen} onClose={closeModal} className="max-w-[700px] m-4">
        <div className="no-scrollbar relative w-full max-w-[700px] overflow-y-auto rounded-3xl bg-white p-4 dark:bg-gray-900 lg:p-11">
          <div className="px-2 pr-14">
            <h4 className="mb-2 text-2xl font-semibold text-gray-800 dark:text-white/90">
              Edit Personal Information
            </h4>
            <p className="mb-6 text-sm text-gray-500 dark:text-gray-400 lg:mb-7">
              Update your details to keep your profile up-to-date.
            </p>
          </div>
          <form className="flex flex-col" onSubmit={handleSubmit(onSubmit)}>
            <div className="custom-scrollbar h-[450px] overflow-y-auto px-2 pb-3">
              {/* <div>
                <h5 className="mb-5 text-lg font-medium text-gray-800 dark:text-white/90 lg:mb-6">
                  Social Links
                </h5>

                <div className="grid grid-cols-1 gap-x-6 gap-y-5 lg:grid-cols-2">
                  <div>
                    <Label>Facebook</Label>
                    <Input
                      type="text"
                      value="https://www.facebook.com/PimjoHQ"
                    />
                  </div>

                  <div>
                    <Label>X.com</Label>
                    <Input type="text" value="https://x.com/PimjoHQ" />
                  </div>

                  <div>
                    <Label>Linkedin</Label>
                    <Input
                      type="text"
                      value="https://www.linkedin.com/company/pimjo"
                    />
                  </div>

                  <div>
                    <Label>Instagram</Label>
                    <Input type="text" value="https://instagram.com/PimjoHQ" />
                  </div>
                </div>
              </div> */}
              <div className="mt-7">
                <h5 className="mb-5 text-lg font-medium text-gray-800 dark:text-white/90 lg:mb-6">
                  Personal Information
                </h5>

                <div className="grid grid-cols-1 gap-x-6 gap-y-5 lg:grid-cols-2">
                  <div className="col-span-2 lg:col-span-1">
                    <Label>First Name</Label>
                    <Input type="text" {...register("name_first")}/>
                  </div>

                  <div className="col-span-2 lg:col-span-1">
                    <Label>Middle Name</Label>
                    <Input type="text" {...register("name_middle")}/>
                  </div>

                  <div className="col-span-2 lg:col-span-1">
                    <Label>Last Name</Label>
                    <Input placeholder="Last name" type="text" {...register("name_last")} />
                  </div>

                  <div className="col-span-2 lg:col-span-1">
                    <Label>Company</Label>
                    <Input type="text" {...register("company")} />
                  </div>

                  <div className="col-span-2">
                    <Label>Role</Label>
                    <Input type="text" value="Super Admin" disabled/>
                  </div>
                </div>
              </div>

              <div className="mt-7">
                <h5 className="mb-5 text-lg font-medium text-gray-800 dark:text-white/90 lg:mb-6">
                 Phones & Emails
                </h5>

                <div className="grid grid-cols-1 gap-x-6 gap-y-5 lg:grid-cols-2">               

                  <div className="col-span-2">
                    <Label>Phone</Label>
                    {phoneFields.map((field, index) => (
                      <div key={field.id} className="flex items-end space-x-2 mb-2">
                        <div className="w-1/4">
                          <Label htmlFor={`phoneNumbers.${index}.format`}>Type</Label>
                          <Controller
                            name={`phoneNumbers.${index}.format`}
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
                          <Label htmlFor={`phoneNumbers.${index}.country_code`}>Code</Label>
                          <Input
                            type="text"
                            id={`phoneNumbers.${index}.country_code`}
                            placeholder="+91"
                            {...register(`phoneNumbers.${index}.country_code`)}
                          />
                          {errors.phoneNumbers?.[index]?.country_code && (
                            <span className="text-red-500 text-sm">
                              {errors.phoneNumbers[index].country_code.message}
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
                    <button
                      type="button"
                      onClick={() => appendPhone({ format: "", country_code: "", number: "" })}
                      className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
                    >
                      <PlusIcon className="mr-2 size-5" />
                      Add Phone Number
                    </button>
                  </div>

                  <div className="col-span-2">
                    <Label>Email</Label>
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
                     <button
                        type="button"
                        onClick={() => appendEmail({ type: "", email: "" })}
                        className="flex items-center mt-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-dark-900"
                      >
                        <PlusIcon className="mr-2 size-5 text-white" />
                        Add Email
                      </button>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3 px-2 mt-6 lg:justify-end">
              <Button size="sm" variant="outline" onClick={closeModal}>
                Close
              </Button>
              <Button size="sm">
                Save Changes
              </Button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}

