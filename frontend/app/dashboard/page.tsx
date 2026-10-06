"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, getOrganization } from "@/lib/api";


export default function DashboardPage() {

  const router = useRouter();

  const [loading, setLoading] = useState(true);

  const [user, setUser] = useState<any>(null);

  const [organization, setOrganization] =
    useState<any>(null);


  useEffect(() => {

    async function loadUser() {

      try {

        const currentUser =
          await getCurrentUser();

        setUser(currentUser);


        const org =
          await getOrganization(
            currentUser.organization_id
          );

        setOrganization(org);

      } catch (error) {

        console.error(error);

        localStorage.removeItem(
          "access_token"
        );

        router.replace("/login");

      } finally {

        setLoading(false);

      }

    }


    loadUser();

  }, [router]);


  if (loading) {

    return (
      <div className="loading-screen">
        Loading your workspace...
      </div>
    );

  }


  return (
    <div
      style={{
        padding: "40px",
      }}
    >

      <h1>
        SubHub Dashboard
      </h1>

      <p>
        Welcome, {user?.email}
      </p>

      <p>
        Role: {user?.role}
      </p>

      <p>
        Organization: {organization?.name}
      </p>

      <p>
        Organization ID: {user?.organization_id}
      </p>

    </div>
  );
}
