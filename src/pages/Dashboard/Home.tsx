import EcommerceMetrics from "../../components/ecommerce/EcommerceMetrics";
import MonthlySalesChart from "../../components/ecommerce/MonthlySalesChart";
import StatisticsChart from "../../components/ecommerce/StatisticsChart";
import MonthlyTarget from "../../components/ecommerce/MonthlyTarget";
import RecentOrders from "../../components/ecommerce/RecentOrders";
import DemographicCard from "../../components/ecommerce/DemographicCard";
import PageMeta from "../../components/common/PageMeta";
import { useAppSelector } from "../../store/hooks";

export default function Home() {
  const { user } = useAppSelector((state) => state.auth);

  console.log("authhhhhhhhhhhh",user?.role)
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <p>Welcome to the CommerceExpert dashboard!</p>
      <div className="mt-4 p-4 bg-blue-50 rounded">
        <p>User Role: {user?.role || 'Not loaded'}</p>
      </div>
    </div>
  );
}
