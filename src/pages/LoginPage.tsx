import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from "../store/hooks";

import { ChevronLeftIcon, EyeCloseIcon, EyeIcon } from '../icons';

import { Input,Label,Button } from '../components/wrapper'
import Checkbox from '../components/form/input/Checkbox';

import { useForm } from "react-hook-form";
import { loginSchema, LoginFormData } from '../validations/auth';
import { zodResolver } from '@hookform/resolvers/zod';
import { login } from '../api/auth';
import { showToast } from '../store/slices/toastSlice';
import { setUser } from '../store/slices/authSlice';


const LoginPage: React.FC = () => {
  
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const { isLoading, error, isAuthenticated } = useAppSelector((state) => state.auth);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, navigate]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      //rememberMe: false,
    },
  });

  const handleFormSubmit = async (data:LoginFormData) => {
       
       try {
              const response = await login(data);             
              if(response.return_status === 1 ) {
                  dispatch(showToast({ message: "Login successful!", type: "success" }));
                  dispatch(setUser({ ...response.return_data.user, isAuthenticated: true }));
                  navigate('/dashboard');
              } else {               
                  dispatch(showToast({ message: response.return_message, type: "error" }));
              }             
       } catch (error : any) {
             dispatch(showToast({ message: error, type: "error" }));
       }   
  };

  const [showPassword, setShowPassword] = useState(false);
  const [isChecked, setIsChecked] = useState(false);
  return (
    <div className="min-h-screen flex">
      {/* Left - Sign In Form */}
      <div className="w-full md:w-1/2 flex flex-col justify-center px-8 md:px-40">
        <a href="#" className="text-sm text-gray-500 mb-6">&larr; Back to dashboard</a>
        <h2 className="text-3xl font-bold mb-2">Sign In</h2>
        <p className="text-sm text-gray-600 mb-6">Enter your email and password to sign in!</p>

        {/* Social Buttons */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-5 mb-8">
              <button className="inline-flex items-center justify-center gap-3 py-3 text-sm font-normal text-gray-700 transition-colors bg-gray-100 rounded-lg px-7 hover:bg-gray-200 hover:text-gray-800 dark:bg-white/5 dark:text-white/90 dark:hover:bg-white/10">
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M18.7511 10.1944C18.7511 9.47495 18.6915 8.94995 18.5626 8.40552H10.1797V11.6527H15.1003C15.0011 12.4597 14.4654 13.675 13.2749 14.4916L13.2582 14.6003L15.9087 16.6126L16.0924 16.6305C17.7788 15.1041 18.7511 12.8583 18.7511 10.1944Z"
                    fill="#4285F4"
                  />
                  <path
                    d="M10.1788 18.75C12.5895 18.75 14.6133 17.9722 16.0915 16.6305L13.274 14.4916C12.5201 15.0068 11.5081 15.3666 10.1788 15.3666C7.81773 15.3666 5.81379 13.8402 5.09944 11.7305L4.99473 11.7392L2.23868 13.8295L2.20264 13.9277C3.67087 16.786 6.68674 18.75 10.1788 18.75Z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.10014 11.7305C4.91165 11.186 4.80257 10.6027 4.80257 9.99992C4.80257 9.3971 4.91165 8.81379 5.09022 8.26935L5.08523 8.1534L2.29464 6.02954L2.20333 6.0721C1.5982 7.25823 1.25098 8.5902 1.25098 9.99992C1.25098 11.4096 1.5982 12.7415 2.20333 13.9277L5.10014 11.7305Z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M10.1789 4.63331C11.8554 4.63331 12.9864 5.34303 13.6312 5.93612L16.1511 3.525C14.6035 2.11528 12.5895 1.25 10.1789 1.25C6.68676 1.25 3.67088 3.21387 2.20264 6.07218L5.08953 8.26943C5.81381 6.15972 7.81776 4.63331 10.1789 4.63331Z"
                    fill="#EB4335"
                  />
                </svg>
                Sign in with Google
              </button>
              <button className="inline-flex items-center justify-center gap-3 py-3 text-sm font-normal text-gray-700 transition-colors bg-gray-100 rounded-lg px-7 hover:bg-gray-200 hover:text-gray-800 dark:bg-white/5 dark:text-white/90 dark:hover:bg-white/10">
                <svg
                  width="21"
                  className="fill-current"
                  height="20"
                  viewBox="0 0 21 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M15.6705 1.875H18.4272L12.4047 8.75833L19.4897 18.125H13.9422L9.59717 12.4442L4.62554 18.125H1.86721L8.30887 10.7625L1.51221 1.875H7.20054L11.128 7.0675L15.6705 1.875ZM14.703 16.475H16.2305L6.37054 3.43833H4.73137L14.703 16.475Z" />
                </svg>
                Sign in with X
              </button>
            </div>

        <div className="flex items-center gap-2 mb-6">
          <hr className="flex-grow border-gray-300" />
          <span className="text-sm text-gray-400">Or</span>
          <hr className="flex-grow border-gray-300" />
        </div>

        <form onSubmit={handleSubmit(handleFormSubmit)} className="flex flex-col gap-4">          
          <div>
            <Label>
              Username <span className=" text-red-500">* { errors.username && errors.username.message}</span>{" "}
            </Label>          
            <Input placeholder="info@gmail.com" {...register('username')} />
          </div>

          <div>
              <Label>
                Password <span className="text-red-500">* { errors.password && errors.password.message}</span>{" "}
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

          <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Checkbox checked={isChecked} onChange={setIsChecked} />
                  <span className="block font-normal text-gray-700 text-theme-sm dark:text-gray-400">
                    Keep me logged in
                  </span>
                </div>
                <Link
                  to="/reset-password"
                  className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400"
                >
                  Forgot password?
                </Link>
          </div>
          
          {/* <Button variant="primary">Sign in </Button> */}
         
                <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-md">
            Sign in
          </button>
               

                  <div className="mt-1">
                      <p className="text-sm font-normal text-center text-gray-700 dark:text-gray-400 sm:text-start">
                        Don&apos;t have an account? {""}
                        <Link
                          to="/signup"
                          className="text-brand-500 hover:text-brand-600 dark:text-brand-400"
                        >
                          Sign Up
                        </Link>
                      </p>
                  </div>
        </form>
      </div>

      {/* Right - Branding */}
      <div className="hidden md:flex w-1/2 bg-[#0F172A] items-center justify-center relative">
        <div className="text-center text-white px-6">
          <div className="flex justify-center mb-4">
            <div className="bg-blue-500 p-3 rounded-xl">
              {/* <svg width="24" height="24" fill="white" viewBox="0 0 24 24">
                <path d="M5 3v18l7-5 7 5V3H5z" />
              </svg> */}
              <img
              src="/images/logo/favicon.png"
              alt="Logo"
              width={32}
              height={32}
            />
            </div>
          </div>
          <h2 className="text-2xl font-semibold">Webclerk</h2>
          <p className="text-sm text-gray-300 mt-2">
             Online Service Provider
          </p>
        </div>

        <div className="absolute bottom-4 right-4">
          <button className="bg-blue-600 p-2 rounded-full">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="white"
              className="w-5 h-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21.752 15.002A9.718 9.718 0 0112 21.75a9.718 9.718 0 01-9.752-6.748 9.715 9.715 0 0112.502-12.502 9.715 9.715 0 016.748 12.502z"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;