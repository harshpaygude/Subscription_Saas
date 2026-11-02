
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  ChevronDown,
  Menu,
  Plus,
  Search,
  X,
  LogOut,
  LayoutDashboard,
  Settings,
  Plug,
  Copy,
  Check,
  Cloud,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";

import {
  getCurrentUser,
  getOrganization,
  logout,
  listAWSConnections,
  setupAWSConnection,
  verifyAWSConnection,
  disconnectAWS,
  getAWSCosts,
  getAWSAccountPlan,
  type AWSAccountPlanResponse,
  type AWSConnection,
  type AWSConnectionSetupResponse,
  type AWSCostResponse,
} from "@/lib/api";
import { ProviderCatalog } from "@/components/integrations/ProviderCatalog";
import { ConnectionStatus } from "@/components/integrations/ConnectionStatus";
import { WizardNavigation } from "@/components/integrations/WizardNavigation";
import { providerRegistry } from "@/components/integrations/providerRegistry";

type SetupStage = "account" | "role";

function CloudIcon() {
  return (
    <span aria-hidden="true" className="sh-cloud-glyph">
      ☁
    </span>
  );
}

const money = (amount: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);

export default function DashboardPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [organization, setOrganization] = useState<any>(null);

  const [showProfile, setShowProfile] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [notice, setNotice] = useState("");

  const [awsConnections, setAwsConnections] = useState<AWSConnection[]>([]);
  const [awsCosts, setAwsCosts] = useState<Record<number, AWSCostResponse>>({});
  const [awsPlans, setAwsPlans] = useState<
    Record<number, AWSAccountPlanResponse>
  >({});
  const [awsPlanErrors, setAwsPlanErrors] = useState<Record<number, string>>({});
  const [awsBusy, setAwsBusy] = useState(false);

  const [showServices, setShowServices] = useState(false);
  const [serviceSearch, setServiceSearch] = useState("");

  // AWS setup wizard state
  const [setupStage, setSetupStage] = useState<SetupStage>("account");
  const [accountId, setAccountId] = useState("");
  const [roleArn, setRoleArn] = useState("");
  const [setupResult, setSetupResult] =
    useState<AWSConnectionSetupResponse | null>(null);
  const [copiedItem, setCopiedItem] = useState("");

  useEffect(() => {
    async function loadUser() {
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);

        const org = await getOrganization(currentUser.organization_id);
        setOrganization(org);

        try {
          const connections = await listAWSConnections();
          setAwsConnections(connections);

          for (const connection of connections) {
            try {
              const plan = await getAWSAccountPlan(connection.id);
              setAwsPlans((current) => ({
                ...current,
                [connection.id]: plan,
              }));
              setAwsPlanErrors((current) => {
                const next = { ...current };
                delete next[connection.id];
                return next;
              });
            } catch (planError) {
              setAwsPlanErrors((current) => ({
                ...current,
                [connection.id]:
                  planError instanceof Error
                    ? planError.message
                    : "AWS account-plan information unavailable.",
              }));
            }
          }
        } catch (awsError) {
          console.error("Could not load AWS connections:", awsError);
          setNotice(
            awsError instanceof Error
              ? awsError.message
              : "Could not load AWS connections."
          );
        }
      } catch (error) {
        console.error(error);
        localStorage.removeItem("access_token");
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [router]);

  function resetAWSWizard() {
    setSetupStage("account");
    setAccountId("");
    setRoleArn("");
    setSetupResult(null);
    setCopiedItem("");
  }

  function closeServices() {
    if (awsBusy) return;
    setShowServices(false);
    resetAWSWizard();
  }

  async function handleSetupAWS() {
    if (!/^\d{12}$/.test(accountId.trim())) {
      setNotice("Enter a valid 12-digit AWS account ID.");
      return;
    }

    setAwsBusy(true);
    setNotice("");

    try {
      const result = await setupAWSConnection(accountId.trim());
      setSetupResult(result);
      setSetupStage("role");
      setNotice(
        "Setup instructions generated. Create the IAM role in the target AWS account, then enter its ARN below."
      );
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not start AWS setup."
      );
    } finally {
      setAwsBusy(false);
    }
  }

  async function handleVerifyAWS() {
    if (!setupResult) {
      setNotice("Generate the AWS setup instructions first.");
      return;
    }

    const arn = roleArn.trim();

    if (
      !/^arn:aws(-us-gov|-cn)?:iam::\d{12}:role\/.+$/.test(arn)
    ) {
      setNotice("Enter a valid AWS IAM role ARN.");
      return;
    }

    const roleAccountId = arn.split(":")[4];

    if (roleAccountId !== setupResult.account_id) {
      setNotice(
        "The account ID in the role ARN does not match the account used during setup."
      );
      return;
    }

    setAwsBusy(true);
    setNotice("");

    try {
      const result = await verifyAWSConnection(
        setupResult.connection_id,
        arn
      );

      setAwsConnections((current) => [
        result.connection,
        ...current.filter((item) => item.id !== result.connection.id),
      ]);

      try {
        const plan = await getAWSAccountPlan(result.connection.id);
        setAwsPlans((current) => ({
          ...current,
          [result.connection.id]: plan,
        }));
        setAwsPlanErrors((current) => {
          const next = { ...current };
          delete next[result.connection.id];
          return next;
        });
      } catch (planError) {
        setAwsPlanErrors((current) => ({
          ...current,
          [result.connection.id]:
            planError instanceof Error
              ? planError.message
              : "AWS account-plan information unavailable.",
        }));
      }

      setNotice(
        result.message +
          (!result.cost_access
            ? " The role was verified, but Cost Explorer access is unavailable."
            : "")
      );

      setShowServices(false);
      resetAWSWizard();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not verify the AWS role."
      );
    } finally {
      setAwsBusy(false);
    }
  }

  async function handleCopy(value: string, item: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedItem(item);
      setNotice(`${item} copied to clipboard.`);
    } catch {
      setNotice(
        "Clipboard access failed. Select and copy the text manually."
      );
    }
  }

  async function handleDisconnectAWS(connectionId: number) {
    if (!window.confirm("Disconnect this AWS account from UniSora?")) return;

    setAwsBusy(true);

    try {
      await disconnectAWS(connectionId);

      setAwsConnections((current) =>
        current.filter((item) => item.id !== connectionId)
      );

      setAwsCosts((current) => {
        const next = { ...current };
        delete next[connectionId];
        return next;
      });

      setAwsPlans((current) => {
        const next = { ...current };
        delete next[connectionId];
        return next;
      });

      setAwsPlanErrors((current) => {
        const next = { ...current };
        delete next[connectionId];
        return next;
      });

      setNotice("AWS account disconnected from UniSora.");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not disconnect AWS."
      );
    } finally {
      setAwsBusy(false);
    }
  }

  async function handleLoadCosts(connectionId: number) {
    setAwsBusy(true);

    try {
      const result = await getAWSCosts(connectionId);
      setAwsCosts((current) => ({
        ...current,
        [connectionId]: result,
      }));
      setNotice("AWS cost data loaded successfully.");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not load AWS costs."
      );
    } finally {
      setAwsBusy(false);
    }
  }

  if (loading) {
    return <div className="loading-screen">Loading your workspace...</div>;
  }

  const firstPlan = awsConnections.length
    ? awsPlans[awsConnections[0].id]
    : undefined;

  const trustPolicyText = setupResult
    ? JSON.stringify(setupResult.trust_policy, null, 2)
    : "";

  return (
    <main className="sh-page">
      <header className="sh-topbar">
        <div className="sh-heading">
          <button
            className="sh-icon-button sh-menu-button"
            aria-label="Toggle navigation"
            onClick={() => setMobileNav((value) => !value)}
          >
            <Menu size={22} />
          </button>
          <div>
            <h1>Dashboard</h1>
            <p>Manage your connected AWS account.</p>
          </div>
        </div>

        <div className="sh-top-actions">
          <div className="sh-pop-wrap">
            <button
              className="sh-icon-button sh-bell"
              aria-label="Notifications"
              onClick={() => setShowNotifications((value) => !value)}
            >
              <Bell size={21} />
            </button>
            {showNotifications && (
              <div className="sh-popover">
                <strong>Notifications</strong>
                <p>You're all caught up.</p>
                <small>AWS account and billing alerts will appear here.</small>
              </div>
            )}
          </div>

          <button
            className="sh-service-button"
            onClick={() => {
              resetAWSWizard();
              setShowServices(true);
            }}
          >
            <Plug size={17} /> Add Service
          </button>

          <div className="sh-pop-wrap">
            <button
              className="sh-user-menu"
              onClick={() => setShowProfile((value) => !value)}
            >
              <span className="sh-avatar">
                {user?.email?.slice(0, 1).toUpperCase() || "U"}
              </span>
              <ChevronDown size={16} />
            </button>
            {showProfile && (
              <div className="sh-popover sh-profile-pop">
                <strong>{user?.email}</strong>
                <span>{organization?.name || "Your workspace"}</span>
                <button onClick={() => logout()}>
                  <LogOut size={15} /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {mobileNav && (
        <nav className="sh-mobile-nav">
          <a className="active" href="/dashboard">
            <LayoutDashboard size={17} /> Dashboard
          </a>
          <a href="#services" onClick={() => setMobileNav(false)}>
            <Plug size={17} /> Connected Services
          </a>
          <a
            href="#settings"
            onClick={(event) => {
              event.preventDefault();
              setNotice(`Workspace: ${organization?.name || "UniSora"}`);
            }}
          >
            <Settings size={17} /> Settings
          </a>
        </nav>
      )}

      <section className="sh-content">
        {notice && (
          <div className="sh-notice" role="status">
            {notice}
            <button
              aria-label="Dismiss"
              onClick={() => setNotice("")}
            >
              <X size={15} />
            </button>
          </div>
        )}

        <div className="sh-stats-grid">
          <article className="sh-stat-card">
            <span>AWS Credits Remaining</span>
            <strong>
              {firstPlan?.credits_remaining != null
                ? money(
                    Number(firstPlan.credits_remaining),
                    firstPlan.currency || "USD"
                  )
                : "—"}
            </strong>
            <small>
              {firstPlan
                ? "Reported by AWS account plan"
                : awsConnections.length
                  ? awsPlanErrors[awsConnections[0].id] ||
                    "Loading AWS plan information"
                  : "Connect AWS to view credits"}
            </small>
          </article>

          <article className="sh-stat-card">
            <span>AWS Plan Status</span>
            <strong>
              {firstPlan?.plan_status ||
                (awsConnections.length ? "Connected" : "Not connected")}
            </strong>
            <small>
              {firstPlan?.plan_type
                ? `${firstPlan.plan_type} plan`
                : "AWS account plan"}
            </small>
          </article>

          <article className="sh-stat-card">
            <span>Days Remaining</span>
            <strong>
              {firstPlan?.days_remaining != null
                ? firstPlan.days_remaining
                : "—"}
            </strong>
            <small>
              {firstPlan?.expiration_date
                ? `Expires ${firstPlan.expiration_date}`
                : "Plan expiry from AWS"}
            </small>
          </article>

          <article className="sh-stat-card">
            <span>Connected AWS Accounts</span>
            <strong>{awsConnections.length}</strong>
            <small>Across this workspace</small>
          </article>
        </div>

        <section className="sh-panel sh-connected-panel" id="services">
          <div className="sh-panel-header">
            <h2>
              Connected Services{" "}
              <span className="sh-count">{awsConnections.length}</span>
            </h2>
            <button
              className="sh-view-all"
              onClick={() => {
                resetAWSWizard();
                setShowServices(true);
              }}
            >
              <Plus size={16} /> Add Service
            </button>
          </div>

          {awsConnections.length === 0 ? (
            <div className="sh-service-empty">
              <span className="sh-aws-icon">
                <CloudIcon />
              </span>
              <div>
                <strong>No AWS account connected yet</strong>
                <p>
                  Connect AWS to view your account plan, credits and cost data.
                </p>
              </div>
              <button
                className="sh-add-button"
                onClick={() => {
                  resetAWSWizard();
                  setShowServices(true);
                }}
              >
                <Plus size={16} /> Connect AWS
              </button>
            </div>
          ) : (
            <div className="sh-connected-list">
              {awsConnections.map((connection) => (
                <article className="sh-connected-card" key={connection.id}>
                  <div className="sh-connected-main">
                    <span className="sh-aws-icon">
                      <CloudIcon />
                    </span>
                    <div>
                      <strong>Amazon Web Services</strong>
                      <p>
                        Account {connection.account_id || "Unknown"} · Region{" "}
                        {connection.region}
                      </p>
                        <ConnectionStatus status={connection.status} />
                    </div>
                  </div>

                  <div className="sh-connected-actions">
                    <div className="sh-cost-result sh-credit-result">
                      <small>AWS account-plan credits remaining</small>
                      <strong>
                        {awsPlans[connection.id]?.credits_remaining != null
                          ? money(
                              Number(
                                awsPlans[connection.id].credits_remaining
                              ),
                              awsPlans[connection.id].currency || "USD"
                            )
                          : "Unavailable"}
                      </strong>
                      <small>
                        {awsPlans[connection.id]
                          ? `${awsPlans[connection.id].plan_type} plan · ${
                              awsPlans[connection.id].days_remaining == null
                                ? "expiry unavailable"
                                : `${awsPlans[connection.id].days_remaining} days remaining`
                            }`
                          : awsPlanErrors[connection.id] ||
                            "Checking AWS account plan..."}
                      </small>
                      {awsPlans[connection.id]?.expiration_date && (
                        <small>
                          Expires {awsPlans[connection.id].expiration_date}
                        </small>
                      )}
                    </div>

                    {awsCosts[connection.id] ? (
                      <div className="sh-cost-result">
                        <small>Month-to-date cost</small>
                        <strong>
                          {money(
                            Number(awsCosts[connection.id].amount || 0),
                            awsCosts[connection.id].currency || "USD"
                          )}
                        </strong>
                        <small>
                          {awsCosts[connection.id].period_start} –{" "}
                          {awsCosts[connection.id].period_end_exclusive}
                        </small>
                      </div>
                    ) : (
                      <button
                        className="sh-secondary-button"
                        disabled={awsBusy}
                        onClick={() => handleLoadCosts(connection.id)}
                      >
                        {awsBusy ? "Loading..." : "Load costs"}
                      </button>
                    )}

                    <button
                      className="sh-disconnect-button"
                      disabled={awsBusy}
                      onClick={() => handleDisconnectAWS(connection.id)}
                    >
                      Disconnect
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="sh-panel sh-spending-panel">
          <div className="sh-panel-header">
            <h2>AWS Spending</h2>
            <span className="sh-total-pill">
              {Object.keys(awsCosts).length ? "Cost Explorer" : "Not loaded"}
            </span>
          </div>

          <div className="sh-spending-body">
            <div className="sh-donut-area">
              <div
                className="sh-donut"
                style={{
                  background: "conic-gradient(#f59e0b 0% 100%)",
                }}
              >
                <div className="sh-donut-hole">
                  <strong>
                    {Object.values(awsCosts).length
                      ? money(
                          Object.values(awsCosts).reduce(
                            (sum, item) => sum + Number(item.amount || 0),
                            0
                          )
                        )
                      : "—"}
                  </strong>
                  <span>Month to date</span>
                </div>
              </div>
            </div>

            <div className="sh-legend">
              <div className="sh-legend-row">
                <span>
                  <i style={{ background: "#f59e0b" }} />
                  AWS service spend
                </span>
                <strong>
                  {Object.values(awsCosts).length
                    ? money(
                        Object.values(awsCosts).reduce(
                          (sum, item) => sum + Number(item.amount || 0),
                          0
                        )
                      )
                    : "Not loaded"}
                </strong>
              </div>
              <p className="sh-demo-note">
                AWS credits and service spending are separate figures. Use
                Load costs on a connected account to retrieve spending from
                Cost Explorer.
              </p>
            </div>
          </div>
        </section>

        <footer className="sh-footer">
          Workspace: <strong>{organization?.name || "UniSora"}</strong>
          <span>Signed in as {user?.email}</span>
        </footer>
      </section>

      {showServices && (
        <div
          className="sh-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeServices();
          }}
        >
          <section
            className="sh-modal sh-services-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="sh-services-title"
          >
            <div className="sh-modal-heading">
              <div>
                <h2 id="sh-services-title">
                  {setupResult ? "Connect AWS account" : "Add a service"}
                </h2>
                <p>
                  {setupResult
                    ? "Configure the IAM role and verify your AWS account."
                    : "Choose a provider to connect to your workspace."}
                </p>
              </div>
              <button
                className="sh-icon-button"
                aria-label="Close"
                onClick={closeServices}
              >
                <X size={20} />
              </button>
            </div>

            {!setupResult ? (
              <>
                <label className="sh-service-search">
                  <Search size={17} />
                  <input
                    value={serviceSearch}
                    onChange={(event) => setServiceSearch(event.target.value)}
                    placeholder="Search services..."
                    autoFocus
                  />
                </label>

                <ProviderCatalog
                  providers={providerRegistry.filter((provider) =>
                    provider.id === "AWS" ? awsConnections.length === 0 : true,
                  )}
                  search={serviceSearch}
                  onSelect={(provider) => {
                    if (provider.id !== "AWS") return;
                    setServiceSearch("");
                    setSetupStage("account");
                    setAccountId("");
                    setSetupResult(null);
                  }}
                />

                {awsConnections.length === 0 && (
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      void handleSetupAWS();
                    }}
                    className="sh-aws-wizard-form"
                  >
                    <h3>Step 1 — AWS account</h3>
                    <p>
                      Enter the 12-digit AWS account ID you want to connect.
                    </p>
                    <label htmlFor="aws-account-id">AWS account ID</label>
                    <input
                      id="aws-account-id"
                      inputMode="numeric"
                      pattern="[0-9]{12}"
                      maxLength={12}
                      value={accountId}
                      onChange={(event) => setAccountId(event.target.value)}
                      placeholder="123456789012"
                      required
                    />
                    <button
                      className="sh-add-button"
                      type="submit"
                      disabled={awsBusy}
                    >
                      {awsBusy ? "Generating instructions..." : "Continue"}
                    </button>
                  </form>
                )}

                <p className="sh-demo-note">
                  UniSora generates a unique external ID for each setup request.
                  You will create a dedicated IAM role in the AWS account
                  before verification.
                </p>
              </>
            ) : (
              <div className="sh-aws-wizard-form">
                <WizardNavigation current={setupStage === "account" ? 1 : 3} total={3} />
                <div className="sh-wizard-step">
                  <ShieldCheck size={22} />
                  <div>
                    <h3>Step 2 — Configure AWS IAM</h3>
                    <p>
                      Create a role in the AWS account below. Use the generated
                      trust policy and external ID for this connection.
                    </p>
                  </div>
                </div>

                <div className="sh-setup-detail">
                  <span>Target AWS account</span>
                  <strong>{setupResult.account_id}</strong>
                </div>

                <div className="sh-setup-detail">
                  <span>UniSora connection ID</span>
                  <strong>{setupResult.connection_id}</strong>
                </div>

                <div className="sh-setup-detail">
                  <span>Trusted principal ARN</span>
                  <code>{setupResult.trusted_principal_arn}</code>
                </div>

                <div className="sh-policy-heading">
                  <label htmlFor="aws-trust-policy">Trust policy JSON</label>
                  <button
                    type="button"
                    className="sh-secondary-button"
                    onClick={() =>
                      void handleCopy(trustPolicyText, "Trust policy")
                    }
                  >
                    {copiedItem === "Trust policy" ? (
                      <Check size={15} />
                    ) : (
                      <Copy size={15} />
                    )}
                    Copy policy
                  </button>
                </div>

                <pre id="aws-trust-policy" className="sh-policy-code">
                  {trustPolicyText}
                </pre>

                <div className="sh-policy-heading">
                  <label htmlFor="aws-external-id">External ID</label>
                  <button
                    type="button"
                    className="sh-secondary-button"
                    onClick={() =>
                      void handleCopy(setupResult.external_id, "External ID")
                    }
                  >
                    {copiedItem === "External ID" ? (
                      <Check size={15} />
                    ) : (
                      <Copy size={15} />
                    )}
                    Copy ID
                  </button>
                </div>

                <input
                  id="aws-external-id"
                  readOnly
                  value={setupResult.external_id}
                  onFocus={(event) => event.currentTarget.select()}
                />

                <a
                  href="https://console.aws.amazon.com/iam/home#/roles"
                  target="_blank"
                  rel="noreferrer"
                  className="sh-aws-console-link"
                >
                  Open AWS IAM Roles <ExternalLink size={15} />
                </a>

                <p className="sh-demo-note">
                  In the target account, create a dedicated IAM role using this
                  trust policy. Attach only the permissions required by your
                  UniSora integration. Do not use AdministratorAccess. Then
                  enter the new role ARN below.
                </p>

                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void handleVerifyAWS();
                  }}
                >
                  <h3>Step 3 — Verify the role</h3>
                  <label htmlFor="aws-role-arn">IAM role ARN</label>
                  <input
                    id="aws-role-arn"
                    value={roleArn}
                    onChange={(event) => setRoleArn(event.target.value)}
                    placeholder="arn:aws:iam::123456789012:role/UniSoraReadOnlyIntegration"
                    required
                  />
                  <button
                    className="sh-add-button"
                    type="submit"
                    disabled={awsBusy}
                  >
                    {awsBusy ? "Verifying role..." : "Verify and connect"}
                  </button>
                </form>

                <button
                  type="button"
                  className="sh-secondary-button"
                  disabled={awsBusy}
                  onClick={() => {
                    resetAWSWizard();
                    setNotice(
                      "Setup cancelled in the UI. The pending backend connection has not been deleted."
                    );
                  }}
                >
                  Start over
                </button>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}

