"use client";

import dynamic from "next/dynamic";

const UWAOceanDashboard = dynamic(() => import("@/components/UWAOceanDashboard"), { ssr: false });

export default function Page() {
  return <UWAOceanDashboard />;
}
