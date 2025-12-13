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
