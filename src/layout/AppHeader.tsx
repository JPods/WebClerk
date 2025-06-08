import { useEffect, useRef, useState } from "react";

import { Link } from "react-router";
import { useSidebar } from "../context/SidebarContext";
import { ThemeToggleButton } from "../components/common/ThemeToggleButton";
import NotificationDropdown from "../components/header/NotificationDropdown";
import UserDropdown from "../components/header/UserDropdown";

const AppHeader: React.FC = () => {
  const [isApplicationMenuOpen, setApplicationMenuOpen] = useState(false);

  const { isMobileOpen, toggleSidebar, toggleMobileSidebar } = useSidebar();

  const handleToggle = () => {
    if (window.innerWidth >= 1024) {
      toggleSidebar();
    } else {
      toggleMobileSidebar();
    }
  };

  const toggleApplicationMenu = () => {
    setApplicationMenuOpen(!isApplicationMenuOpen);
  };

  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <>
<header className="sticky top-0 flex w-full bg-[#F5F5F5] z-1 dark:border-gray-800 dark:bg-gray-900 ">
    <div className="w-full px-3 py-3 lg:py-0 lg:px-0">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {/* Title and subtitle */}
        <div className=" pl-12">
          <h1 className="text-3xl text-[#333333] dark:text-white">
            Mobile Devices
          </h1>
          <p className="text-base font-400 text-[#333333] dark:text-gray-400">
            Issue and Return
          </p>
        </div>

    {/* Search and controls */}
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4 pr-6 lg:pt-8 lg:pb-2 pl-8">
      {/* Search input */}
      <div className="relative w-full sm:w-64 lg:w-72">
        <input
          type="text"
          placeholder="Search"
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 pr-10 text-sm text-gray-800 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white dark:placeholder:text-gray-500"
        />
        <div className="absolute inset-y-0 right-3 flex items-center">
          <svg
            className="w-4 h-4 text-gray-500 dark:text-gray-400"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path d="M21 21l-4.35-4.35M10 18a8 8 0 100-16 8 8 0 000 16z" />
          </svg>
        </div>
      </div>

      {/* Date Picker Placeholder */}
      <div className="w-full sm:w-auto">
        <input
          type="text"
          value="23-04-2025 - 23-04-2025"
          className="w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-800 shadow-sm focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-white"
          readOnly
        />
      </div>

      {/* Filter Button */}
      <button className="flex items-center justify-center gap-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-800 shadow-sm hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-900 dark:text-white dark:hover:bg-gray-800">
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L15 13.414V19a1 1 0 01-1.447.894l-4-2A1 1 0 019 17v-3.586L3.293 6.707A1 1 0 013 6V4z" />
        </svg>
        Filter
      </button>

      {/* More Options */}
      <button className="rounded-lg border border-gray-300 bg-white p-2 text-gray-700 shadow-sm hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-900 dark:text-white dark:hover:bg-gray-800">
        <svg
          className="w-5 h-5"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M6 10a2 2 0 11-4 0 2 2 0 014 0zm6 0a2 2 0 11-4 0 2 2 0 014 0zm6 0a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </button>
    </div>
  </div>
</div>
</header>
<div className=" border-t border-gray-300 w-[calc(100%-5rem)] ml-12 mt-[6px]"></div>
</>
  );
};

export default AppHeader;
