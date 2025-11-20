import { zodResolver } from '@hookform/resolvers/zod';
import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { EmailVerifyFormData, emailVerifySchema } from '../../validations/auth';
import Label from '../form/Label';
import { Input } from '../wrapper';
import { verifyEmail } from '../../api/auth';
import { useNavigate } from 'react-router';
import { PageRoutes } from '../../routes/Routes';
import { useDispatch } from 'react-redux';
import { showToast } from '../../store/slices/toastSlice';

interface PersonalInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  data?: string;
}

const ModalForm: React.FC<PersonalInfoModalProps> = ({ isOpen, onClose, data = '' }) => {
  if (!isOpen) return null;
   
  const navigate = useNavigate()
  const dispatch = useDispatch()
  useEffect(() => {
      setValue('email', data)
  },[])
  const {
        register,
        handleSubmit,
        setValue,
        formState: { errors },
      } = useForm<EmailVerifyFormData>({
        resolver: zodResolver(emailVerifySchema),
        defaultValues: {
          //rememberMe: false,
        },
      });

    const handleFormSubmit = async (data:EmailVerifyFormData) => {
             try {
                const res = await verifyEmail(data)
                if(res)
                 {
                   dispatch(showToast({ message: "You are verified. Now login to your A/c", type: "success" }));
                   navigate(PageRoutes.login)
                   onClose()
                 }
             } catch (error) {
                console.log("error")
             }
    }

  return (
    <div className="fixed inset-0 backdrop-blur-sm bg-black/30 flex justify-center items-center z-50">
      <div className="bg-white rounded-2xl p-8 w-full max-w-lg relative shadow-lg m-2">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 text-xl"
        >
          &times;
        </button>

        {/* Modal Content */}
        <h2 className="text-xl font-semibold mb-6 text-gray-800">Please verify your email</h2>
        <form onSubmit={handleSubmit(handleFormSubmit)}>
        <div  className="grid grid-cols-1 gap-4">
           <div>
                <Label>
                    Email<span className="text-error-500">* { errors.email && errors.email.message}</span>
                </Label>
                <Input
                    type="email"
                    id="email"                      
                    placeholder="Enter your email"
                    {...register('email')}
                    disabled
                />
            </div>

          <div>
                <Label>
                    Verification code<span className="text-error-500">* { errors.code && errors.code.message}</span>
                </Label>
                <Input
                    type="text"
                    id="code"                      
                    placeholder="Enter verification code"
                    {...register('code')}
                />
          </div>          
        </div>

        {/* Buttons */}
        <div className="flex justify-end mt-6 gap-3">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100"
          >
            Close
          </button>
          <button
            type="submit"
            className="px-5 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
          >
            Save Changes
          </button>
        </div>
        </form>
      </div>
    </div>
  );
};

export default ModalForm;
