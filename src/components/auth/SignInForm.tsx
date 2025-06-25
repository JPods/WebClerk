import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { ChevronLeftIcon, EyeCloseIcon, EyeIcon } from "../../icons";
import Label from "../form/Label";
import Input from "../form/input/InputField";
import Checkbox from "../form/input/Checkbox";
import Button from "../ui/button/Button";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { LoginFormData, loginSchema } from "../../validations/auth";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from '@hookform/resolvers/zod';
import { login, userDetails } from "../../api/auth";
import { showToast } from "../../store/slices/toastSlice";
import { setUser } from "../../store/slices/authSlice";
import { PageRoutes } from "../../routes/Routes";
import Select from "../form/Select";
import axiosInstance from "../../api/axios";
import { PostLoginURL } from "../../routes/network";


export default function SignInForm() {

  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const { user, isLoading, error, isAuthenticated } = useAppSelector((state) => state.auth);
  
   console.log("User data",user)
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      //rememberMe: false,
    },
  });

  const handleFormSubmit = async (data:any) => {
          // Overwritten on the backend by user profile
             data.role = 'USER';
       try {
              const response = await login(data);              
              if(response.status === 200 ) {
                  localStorage.setItem("accessToken", response.data.access);
                  localStorage.setItem("refreshToken", response.data.refresh);

                       const res = await axiosInstance.get(PostLoginURL.getUser,{
                            headers: {
                              Authorization: `Bearer ${response.data.access}`,
                            },
                          });
                        if(res.status === 200)
                        {   
                            const { id, uuid, email, role, name_first, name_last, rank } = res.data;
                            const user = {id, uuid,email,role,name_first,name_last,rank};
                            dispatch(setUser(user));  
                            dispatch(showToast({ message: "Login successful!", type: "success" }));
                            navigate('/dashboard');
                        }    
                 
                       // dispatch(setUser({ ...response.data.access, isAuthenticated: true }));
                 
              } else {               
                  dispatch(showToast({ message: response.error[0] ?? "Try again later", type: "error" }));
              }             
       } catch (error : any) {
             dispatch(showToast({ message: error, type: "error" }));
       }   
  };
  const [showPassword, setShowPassword] = useState(false);
  const [isChecked, setIsChecked] = useState(false);

  //  const selectOption = [                          
  //                         {value:"ADMIN", label:"ADMIN"},
  //                         {value:"SUPER", label:"SUPER"},
  //                         {value:"SALE", label:"Sales"},
  //                         {value:"REP", label:"Representative"},
  //                         {value:"VENDOR", label:"Vendor"}, 
  //                         {value:"CUSTOMER", label:"Customer"},
  //                         {value:"USER", label:"User"},
  //                         {value:"PUBLIC", label:"Public"},                                                   
  //                        ]
  return (
    <div className="flex flex-col flex-1">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              Sign In
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Enter your email and password to sign in!
            </p>
          </div>
          <div>

          <form onSubmit={handleSubmit(handleFormSubmit)}>              
              <div className="space-y-6">
                <div>
                  <Label>
                    Email <span className="text-error-500">* { errors.email && errors.email.message}</span>{" "}
                  </Label>
                  <Input placeholder="info@gmail.com" {...register('email')}/>
                </div>
                <div>
                  <Label>
                    Password <span className="text-error-500">* { errors.password && errors.password.message} </span>{" "}
                  </Label>
                  <div className="relative">
                    <Input
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
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
                {/* <div>
                    <Label>
                    Role <span className="text-error-500">* { errors.role && errors.role.message} </span>{" "}
                  </Label>
                    <Controller
                      name="role"
                      control={control}
                      defaultValue="customer"
                      render={({ field }) => (
                        <Select
                          options={selectOption}                          
                          onChange={field.onChange}
                          defaultValue={field.value}
                        />
                      )}
                    />         
                </div> */}
                <div className="flex items-center justify-between">
                  {/* <div className="flex items-center gap-3">
                    <Checkbox checked={isChecked} onChange={setIsChecked} />
                    <span className="block font-normal text-gray-700 text-theme-sm dark:text-gray-400">
                      Keep me logged in
                    </span>
                  </div> */}
                  <Link
                    to="/reset-password"
                    className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div>
                  <Button className="w-full" size="sm">
                    Sign in
                  </Button>
                </div>
              </div>
          </form>

          <div className="mt-5">
              <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-400 sm:text-start">
                Don&apos;t have an account? {""}
                <Link
                  to={PageRoutes.register}
                  className="text-brand-500 hover:text-brand-600 dark:text-brand-400"
                >
                  Sign Up
                </Link>
              </p>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
}
