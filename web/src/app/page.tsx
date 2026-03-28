import { Suspense } from "react";
import { DashboardView } from "./dashboard/DashboardView";

export default function DashboardPage() {
  return (
    <Suspense>
      <DashboardView />
    </Suspense>
  );
}
