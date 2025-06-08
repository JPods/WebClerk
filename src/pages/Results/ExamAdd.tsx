import React, { useState } from 'react';
import { Button, FormSection, InputField, RadioGroup, RangeInputField, SelectField } from '../../components/wrapper';
import MultiSelect from '../../components/form/MultiSelect';


// Assuming you'd have more robust state management or a form library for real-world use
interface FormData {
  date: string;
  class: string;
  division: string;
  testType: 'regular' | 'major';
  testNo: string;
  subject: string;
  testName: string;
  testCode: string;
  maxMarks: string;
  positiveMarks: string;
  negativeMarks: string;
  physicsStartNo: string;
  physicsEndNo: string;
  chemistryStartNo: string;
  chemistryEndNo: string;
  biologyStartNo: string;
  biologyEndNo: string;
  mathStartNo: string;
  mathEndNo: string;
}

const ExamAdd: React.FC = () => {
  const [formData, setFormData] = useState<FormData>({
    date: '10/12/2025',
    class: '',
    division: '',
    testType: 'regular',
    testNo: '',
    subject: '',
    testName: '',
    testCode: '',
    maxMarks: '',
    positiveMarks: '',
    negativeMarks: '',
    physicsStartNo: '',
    physicsEndNo: '',
    chemistryStartNo: '',
    chemistryEndNo: '',
    biologyStartNo: '',
    biologyEndNo: '',
    mathStartNo: '',
    mathEndNo: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleRadioChange = (name: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form Submitted:', formData);
    // Here you would typically send data to your backend API
    alert('Form submitted! Check console for data.');
  };

  // Dummy data for select fields
  const classOptions = [
    { value: 'class-8', label: 'Class 8' },
    { value: 'class-9', label: 'Class 9' },
    { value: 'class-10', label: 'Class 10' },
  ];
  const divisionOptions = [
    { value: 'a', label: 'A' },
    { value: 'b', label: 'B' },
    { value: 'c', label: 'C' },
  ];
  const subjectOptions = [
    { value: 'physics', label: 'Physics' },
    { value: 'chemistry', label: 'Chemistry' },
    { value: 'biology', label: 'Biology' },
    { value: 'math', label: 'Math' },
  ];

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-8xl mx-auto bg-white rounded-2xl shadow-xl p-4 sm:p-4 lg:p-8">
        <h1 className="poppins-text-500 text-base md:text-lg 2xl:text-2xl text-[#333333] mb-2">Create New Test</h1>
       <div className='border rounded-2xl border-[#B6B6B6] p-2 sm:p-4 lg:p-6'>
            <form onSubmit={handleSubmit} className="space-y-6">
          {/* Top Row: Audience, Test Identification, Marking Scheme */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            <FormSection title="Test Details">
              <div className='flex flex-col xl:flex-row justify-between gap-4'>
                    <RadioGroup
                        label="Test Type"
                        name="testType"
                        options={[
                        { value: 'regular', label: 'Regular' },
                        { value: 'major', label: 'Major' },
                        ]}
                        selectedValue={formData.testType}
                        onChange={(value) => handleRadioChange('testType', value as 'regular' | 'major')}
                        required
                    />
                    <InputField
                        label="Test No."
                        id="testNo"
                        placeholder="Test no."
                        value={formData.testNo}
                        onChange={handleChange}
                        required
                    />
              </div>
              
              <SelectField
                label="Subject"
                id="subject"
                options={subjectOptions}
                value={formData.subject}
                onChange={handleChange}
                required
                placeholder="Select your subject"
              />
              <InputField
                label="Test Name"
                id="testName"
                placeholder="Enter test name"
                value={formData.testName}
                onChange={handleChange}
                required
              />
              <InputField
                label="Test Code"
                id="testCode"
                placeholder="Enter test code"
                value={formData.testCode}
                onChange={handleChange}

                required
              />
            </FormSection>
            
            <FormSection title="Student Details">
              <InputField
                label="Date"
                id="date"
                type="date"
                placeholder="dd/mm/yyyy"
                value={formData.date}
                onChange={handleChange}
                required
                //icon={<span className="text-gray-400">📅</span>} 
              />
              <SelectField
                label="Class"
                id="class"
                options={classOptions}
                value={formData.class}
                onChange={handleChange}
                required
                placeholder="Select your class"
              />
              <SelectField
                label="Division"
                id="division"
                options={divisionOptions}
                value={formData.division}
                onChange={handleChange}
                required
                placeholder="Select your division"
              />
              <MultiSelect label='' options={divisionOptions} defaultSelected={[]} onChange={handleChange} disabled/>
            </FormSection>            

            <FormSection title="Marking Scheme">
              <InputField
                label="Max Marks"
                id="maxMarks"
                type="number"
                placeholder="Enter max marks"
                value={formData.maxMarks}
                onChange={handleChange}
                required
              />
              <InputField
                label="Positive Marks"
                id="positiveMarks"
                type="number"
                placeholder="Enter Positive marks"
                value={formData.positiveMarks}
                onChange={handleChange}
                required
              />
              <InputField
                label="Negative Marks"
                id="negativeMarks"
                type="number"
                placeholder="Enter Negative marks"
                value={formData.negativeMarks}
                onChange={handleChange}
                required
              />
            </FormSection>
          </div>

          {/* Bottom Row: Question Details */}
          <FormSection title="Question Details" className="col-span-full">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4">
             <RangeInputField
                label="Physics"
                startId="physicsStartNo"
                endId="physicsEndNo"
                startValue={formData.physicsStartNo}
                endValue={formData.physicsEndNo}
                onStartChange={handleChange}
                onEndChange={handleChange}
              />

              {/* Chemistry */}
              <RangeInputField
                label="Chemistry"
                startId="chemistryStartNo"
                endId="chemistryEndNo"
                startValue={formData.chemistryStartNo}
                endValue={formData.chemistryEndNo}
                onStartChange={handleChange}
                onEndChange={handleChange}
              />
            </div>
          </FormSection>

          {/* Action Buttons */}
          <div className="flex justify-end space-x-4 mt-6">
            <Button type="button" variant="secondary" onClick={() => console.log('Cancel')}>
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Submit
            </Button>
          </div>
        </form>
       </div>
        
      </div>
    </div>
  );
};

export default ExamAdd;