import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../form/Label";
import Input from "../form/input/InputField";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { RegisterFormData, registerSchema } from "../../validations/auth";

import { PageRoutes } from "../../routes/Routes";
import { showToast } from "../../store/slices/toastSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";

import { signup } from "../../api/auth";

import { ModalForm } from "../wrapper";
import Spinner from "../ui/Spinner";

export default function SignUpForm() {
  const [modalOpen, setModalOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [data, setData] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
 

  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const { isAuthenticated } = useAppSelector((state) => state.auth);

    useEffect(() => {
      if (isAuthenticated) {
        navigate(PageRoutes.dashboard);
      }
    }, [isAuthenticated, navigate]);

  const {
      register,
      handleSubmit,
      formState: { errors },
    } = useForm<RegisterFormData>({
      resolver: zodResolver(registerSchema),
      defaultValues: {
        //rememberMe: false,
      },
    });

    const handleFormSubmit = async (data:RegisterFormData) => {
          
           try {
           setSubmitting(true);
           const response = await signup(data);                  
           if(response) {  
             setModalOpen(true)
             setData(data.email)
             // navigate(PageRoutes.login);
           } else {               
             dispatch(showToast({ message: "Try again later", type: "error" }));
           }             
        } catch (error:any) {
          dispatch(showToast({ message: error, type: "error" }));
        } finally {
          setSubmitting(false);
        }  
      };
    
    // const selectOption = [                          
    //                       {value:"ADMIN", label:"ADMIN"},
    //                       {value:"SUPER", label:"SUPER"},
    //                       {value:"SALE", label:"Sales"},
    //                       {value:"REP", label:"Representative"},
    //                       {value:"VENDOR", label:"Vendor"}, 
    //                       {value:"CUSTOMER", label:"Customer"},
    //                       {value:"USER", label:"User"},
    //                       {value:"PUBLIC", label:"Public"},                                                   
    //                      ]
  return (
    <div className="flex flex-col flex-1 w-full overflow-y-auto lg:w-1/2 no-scrollbar">      
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              Sign Up
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Enter your email and password to sign up!
            </p>
          </div>
          <div>
           
            <form onSubmit={handleSubmit(handleFormSubmit)}>
              <div className="space-y-5">
                <div>
                    <Label>
                      email<span className="text-error-500">* { errors.email && errors.email.message}</span>
                    </Label>
                    <Input
                      type="email"
                      id="email"                      
                      placeholder="email"
                      {...register('email')}
                    />
                </div>
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">                  
                  {/* <!-- First Name --> */}
                  <div className="sm:col-span-1">
                    <Label>
                      name_first<span className="text-error-500">* { errors.name_first && errors.name_first.message}</span>
                    </Label>
                    <Input
                      type="text"
                      id="fname"
                      {...register('name_first')}
                      placeholder="name_first"
                    />
                  </div>
                  {/* <!-- Last Name --> */}
                  <div className="sm:col-span-1">
                    <Label>
                      name_last<span className="text-error-500">* { errors.name_last && errors.name_last.message}</span>
                    </Label>
                    <Input
                      type="text"
                      id="lname"
                      {...register('name_last')}
                      placeholder="name_last"
                    />
                  </div>
                </div>
                 <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">                  
                  {/* <!-- First Name --> */}
                  <div className="sm:col-span-1">
                    <Label>
                      password<span className="text-error-500">* { errors.password && errors.password.message}</span>
                    </Label>
                    <div className="relative">
                      <Input
                        placeholder="password"
                        type={showPassword ? "text" : "password"}
                         {...register('password')}
                      />
                      <span
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                      >
                          {showPassword ? (
                            <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                          ) : (
                            <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                          )}
                      </span>
                    </div>
                  </div>
                  {/* <!-- Last Name --> */}
                  <div className="sm:col-span-1">
                    <Label>
                      confirm_password<span className="text-error-500">* { errors.confirmPassword && errors.confirmPassword.message}</span>
                    </Label>
                      <div className="relative">
                        <Input
                          placeholder="confirm_password"
                          type={showPassword ? "text" : "password"}
                           {...register('confirmPassword')}
                        />
                        <span
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                        >
                            {showPassword ? (
                              <EyeIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                            ) : (
                              <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400 size-5" />
                            )}
                        </span>
                      </div>
                  </div>
                </div>
          
                {/* <!-- Role --> */}
                {/* <div>
                  <Label>
                    Role<span className="text-error-500">* { errors.role && errors.role.message}</span>
                  </Label>
                   <Controller
                      name="role"
                      control={control}
                      defaultValue={["USER"]}
                      render={({ field }) => (
                        <MultiSelect
                          options={selectOption}                          
                          onChange={field.onChange}
                          defaultSelected={Array.isArray(field.value) ? field.value : [field.value]}
                        />
                      )}
                    />                 
                </div> */}
                {/* <!-- Checkbox --> */}
                {/* <div className="flex items-center gap-3">
                  <Checkbox
                    className="w-5 h-5"
                    checked={isChecked}
                    onChange={setIsChecked}
                  />
                  <p className="inline-block font-normal text-gray-500 dark:text-gray-400">
                    By creating an account means you agree to the{" "}
                    <span className="text-gray-800 dark:text-white/90">
                      Terms and Conditions,
                    </span>{" "}
                    and our{" "}
                    <span className="text-gray-800 dark:text-white">
                      Privacy Policy
                    </span>
                  </p>
                </div> */}
                {/* <!-- Button --> */}
                <div>
                  <button
                    className="flex items-center justify-center w-full px-4 py-3 text-sm font-medium text-white transition rounded-lg bg-brand-500 shadow-theme-xs hover:bg-brand-600 disabled:opacity-70 disabled:cursor-not-allowed"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <span className="flex items-center gap-2">
                        <Spinner size="sm" />
                        Signing up...
                      </span>
                    ) : (
                      "Sign Up"
                    )}
                  </button>
                </div>
              </div>
            </form>

            <div className="mt-5">
              <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-400 sm:text-start">
                Already have an account? {""}
                <Link
                  to={PageRoutes.login}
                  className="text-brand-500 hover:text-brand-600 dark:text-brand-400"
                >
                  Sign In
                </Link>
              </p>
            </div>
          </div> 
              <ModalForm data={data} isOpen={modalOpen} onClose={() => setModalOpen(false)} />           
        </div>
      </div>
    </div>
  );
}
