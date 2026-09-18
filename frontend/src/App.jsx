import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';

// Layout
import AppLayout from './components/layout/AppLayout';

// Auth Pages
import LoginPage from './pages/auth/LoginPage';

// User Space Pages
import UserDashboard from './pages/user/UserDashboard';
import ClientListPage from './pages/user/clients/ClientListPage';
import ClientDetailPage from './pages/user/clients/ClientDetailPage';
import QuoteListPage from './pages/user/quotes/QuoteListPage';
import NewAutoQuotePage from './pages/user/quotes/NewAutoQuotePage';
import NewMrhQuotePage from './pages/user/quotes/NewMrhQuotePage';
import NewSanteQuotePage from './pages/user/quotes/NewSanteQuotePage';
import NewIaQuotePage from './pages/user/quotes/NewIaQuotePage';
import NewVoyageQuotePage from './pages/user/quotes/NewVoyageQuotePage';
import NewTransportQuotePage from './pages/user/quotes/NewTransportQuotePage';
import ContractListPage from './pages/user/contracts/ContractListPage';
import ContractDetailPage from './pages/user/contracts/ContractDetailPage';
import EndorsementPage from './pages/user/endorsements/EndorsementPage';
import CashCollectionPage from './pages/user/cash/CashCollectionPage';
import ChequeManagementPage from './pages/user/cash/ChequeManagementPage';
import AsaciPage from './pages/user/asaci/AsaciPage';
import MyDerogationsPage from './pages/user/derogations/MyDerogationsPage';

// Admin Space Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import CimaReportsPage from './pages/admin/reporting/CimaReportsPage';
import EmissionSummaryPage from './pages/admin/reporting/EmissionSummaryPage';
import ApprovalCenterPage from './pages/admin/approvals/ApprovalCenterPage';
import CompanyRemittancePage from './pages/admin/remittances/CompanyRemittancePage';
import CommissionDashboardPage from './pages/admin/commissions/CommissionDashboardPage';
import UserManagementPage from './pages/admin/users/UserManagementPage';
import ProfileManagementPage from './pages/admin/users/ProfileManagementPage';
import RolesPermissionsPage from './pages/admin/users/RolesPermissionsPage';
import CatalogCompaniesPage from './pages/admin/settings/CatalogCompaniesPage';
import CatalogProductsPage from './pages/admin/settings/CatalogProductsPage';
import CatalogTarifsPage from './pages/admin/settings/CatalogTarifsPage';
import VehicleGeoSettingsPage from './pages/admin/settings/VehicleGeoSettingsPage';
import { SecteursActivitePage } from './pages/admin/settings/SecteursActivitePage';
import { TypeSouscripteurPage } from './pages/admin/settings/TypeSouscripteurPage';
import { TypeAssurePage } from './pages/admin/settings/TypeAssurePage';
import { ProfessionsPage } from './pages/admin/settings/ProfessionsPage';
import ParametrageGarantiesPage from './pages/admin/settings/ParametrageGarantiesPage';
import ParametrageOffresPage from './pages/admin/settings/ParametrageOffresPage';
import ParametrageTaxesPage from './pages/admin/settings/ParametrageTaxesPage';
import ParametrageMarquesPage from './pages/admin/settings/ParametrageMarquesPage';
import ParametrageCommissionsPage from './pages/admin/settings/ParametrageCommissionsPage';
import ParametrageFlottePage from './pages/admin/settings/ParametrageFlottePage';
import ParametrageSecuritePage from './pages/admin/settings/ParametrageSecuritePage';

// New Institutional Modules (LE PHARE V2)
import CrmPipelinePage from './pages/user/crm/CrmPipelinePage';
import Customer360Page from './pages/user/crm/Customer360Page';
import ClaimsListPage from './pages/user/claims/ClaimsListPage';
import ClaimDetailPage from './pages/user/claims/ClaimDetailPage';
import DocumentManagementPage from './pages/user/documents/DocumentManagementPage';
import ConventionsEnginePage from './pages/admin/conventions/ConventionsEnginePage';
import ComplianceAuditPage from './pages/admin/compliance/ComplianceAuditPage';

// Protected Route Guard
const ProtectedRoute = ({ children }) => {
  const auth = useAuth() || {};
  const { isAuthenticated = false } = auth;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

// Admin / Direction Route Guard (Accès exclusif Directeur ou Administrateur)
const AdminRoute = ({ children }) => {
  const auth = useAuth() || {};
  const { isAuthenticated = false, isDirectorOrAdmin = false } = auth;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!isDirectorOrAdmin) {
    return <Navigate to="/user/dashboard" replace />;
  }
  return children;
};

// Default Route Redirector
const DefaultRedirect = () => {
  const auth = useAuth() || {};
  const { activeSpace = 'user', isDirectorOrAdmin = false } = auth;
  if (!isDirectorOrAdmin) {
    return <Navigate to="/user/dashboard" replace />;
  }
  return <Navigate to={activeSpace === 'admin' ? '/admin/dashboard' : '/user/dashboard'} replace />;
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              {/* Public Login */}
              <Route path="/login" element={<LoginPage />} />

              {/* Authenticated Workspace */}
              <Route
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/" element={<DefaultRedirect />} />

                {/* ===== ESPACE OPÉRATEUR / UTILISATEUR ===== */}
                <Route path="/user/dashboard" element={<UserDashboard />} />
                {/* ===== MODULE C – CRM & RELATION CLIENT ===== */}
                <Route path="/user/crm" element={<CrmPipelinePage />} />
                <Route path="/user/crm/360" element={<Customer360Page />} />

                {/* ===== MODULE D – PROSPECTION & DEVIS ===== */}
                <Route path="/user/clients" element={<ClientListPage />} />
                <Route path="/user/clients/:id" element={<ClientDetailPage />} />
                <Route path="/user/quotes" element={<QuoteListPage />} />
                <Route path="/user/quotes/auto" element={<NewAutoQuotePage />} />
                <Route path="/user/quotes/mrh" element={<NewMrhQuotePage />} />
                <Route path="/user/quotes/sante" element={<NewSanteQuotePage />} />
                <Route path="/user/quotes/ia" element={<NewIaQuotePage />} />
                <Route path="/user/quotes/voyage" element={<NewVoyageQuotePage />} />
                <Route path="/user/quotes/transport" element={<NewTransportQuotePage />} />

                {/* ===== MODULE E – PORTEFEUILLE CONTRATS ===== */}
                <Route path="/user/contracts" element={<ContractListPage />} />
                <Route path="/user/contracts/:id" element={<ContractDetailPage />} />
                <Route path="/user/endorsements" element={<EndorsementPage />} />
                <Route path="/user/asaci" element={<AsaciPage />} />

                {/* ===== MODULE F – ENCAISSEMENT & TRÉSORERIE ===== */}
                <Route path="/user/cash" element={<CashCollectionPage />} />
                <Route path="/user/cheques" element={<ChequeManagementPage />} />

                {/* ===== MODULE H – SINISTRES DÉLÉGUÉS ===== */}
                <Route path="/user/claims" element={<ClaimsListPage />} />
                <Route path="/user/claims/detail" element={<ClaimDetailPage />} />

                {/* ===== MODULE J – GED & WORKFLOWS ===== */}
                <Route path="/user/documents" element={<DocumentManagementPage />} />
                <Route path="/user/derogations" element={<MyDerogationsPage />} />

                {/* ===== ESPACE ADMINISTRATION / DIRECTION (DIRECTEUR & ADMIN SEULEMENT) ===== */}
                <Route path="/admin/dashboard" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
                <Route path="/admin/conventions" element={<AdminRoute><ConventionsEnginePage /></AdminRoute>} />
                <Route path="/admin/compliance" element={<AdminRoute><ComplianceAuditPage /></AdminRoute>} />
                <Route path="/admin/reporting/cima" element={<AdminRoute><CimaReportsPage /></AdminRoute>} />
                <Route path="/admin/reporting/emissions" element={<AdminRoute><EmissionSummaryPage /></AdminRoute>} />
                <Route path="/admin/approvals" element={<AdminRoute><ApprovalCenterPage /></AdminRoute>} />
                <Route path="/admin/remittances" element={<AdminRoute><CompanyRemittancePage /></AdminRoute>} />
                <Route path="/admin/commissions" element={<AdminRoute><CommissionDashboardPage /></AdminRoute>} />
                <Route path="/admin/users" element={<AdminRoute><UserManagementPage /></AdminRoute>} />
                <Route path="/admin/profiles" element={<AdminRoute><ProfileManagementPage /></AdminRoute>} />
                <Route path="/admin/roles-permissions" element={<AdminRoute><RolesPermissionsPage /></AdminRoute>} />
                <Route path="/admin/settings/companies" element={<AdminRoute><CatalogCompaniesPage /></AdminRoute>} />
                <Route path="/admin/settings/products" element={<AdminRoute><CatalogProductsPage initialTab="products" /></AdminRoute>} />
                <Route path="/admin/settings/guarantees" element={<AdminRoute><CatalogProductsPage initialTab="guarantees" /></AdminRoute>} />
                <Route path="/admin/settings/tarifs" element={<AdminRoute><CatalogTarifsPage /></AdminRoute>} />
                <Route path="/admin/settings/vehicle-geo" element={<AdminRoute><VehicleGeoSettingsPage /></AdminRoute>} />
                <Route path="/admin/settings/secteurs-activite" element={<AdminRoute><SecteursActivitePage /></AdminRoute>} />
                <Route path="/admin/settings/professions" element={<AdminRoute><ProfessionsPage /></AdminRoute>} />
                <Route path="/admin/settings/types-souscripteur" element={<AdminRoute><TypeSouscripteurPage /></AdminRoute>} />
                <Route path="/admin/settings/types-assure" element={<AdminRoute><TypeAssurePage /></AdminRoute>} />
                {/* Modules de Paramétrage OREOLE Fidèles */}
                <Route path="/admin/settings/garanties-oreole" element={<AdminRoute><ParametrageGarantiesPage /></AdminRoute>} />
                <Route path="/admin/settings/offres" element={<AdminRoute><ParametrageOffresPage /></AdminRoute>} />
                <Route path="/admin/settings/taxes" element={<AdminRoute><ParametrageTaxesPage /></AdminRoute>} />
                <Route path="/admin/settings/marques" element={<AdminRoute><ParametrageMarquesPage /></AdminRoute>} />
                <Route path="/admin/settings/commissions-baremes" element={<AdminRoute><ParametrageCommissionsPage /></AdminRoute>} />
                <Route path="/admin/settings/flotte" element={<AdminRoute><ParametrageFlottePage /></AdminRoute>} />
                <Route path="/admin/settings/securite-routiere" element={<AdminRoute><ParametrageSecuritePage /></AdminRoute>} />

                {/* Alias direct pour compatibilité stricte OREOLE */}
                <Route path="/parametrage/garanties" element={<Navigate to="/admin/settings/garanties-oreole" replace />} />
                <Route path="/parametrage/sous-garanties" element={<Navigate to="/admin/settings/garanties-oreole" replace />} />
                <Route path="/parametrage/offre" element={<Navigate to="/admin/settings/offres" replace />} />
                <Route path="/parametrage/offre-garantie" element={<Navigate to="/admin/settings/offres" replace />} />
                <Route path="/parametrage/taux-taxe" element={<Navigate to="/admin/settings/taxes" replace />} />
                <Route path="/parametrage/marque-vehicule" element={<Navigate to="/admin/settings/marques" replace />} />
                <Route path="/parametrage/taux-commission" element={<Navigate to="/admin/settings/commissions-baremes" replace />} />
                <Route path="/parametrage/reduction-flotte" element={<Navigate to="/admin/settings/flotte" replace />} />
                <Route path="/parametrage/formule-securite" element={<Navigate to="/admin/settings/securite-routiere" replace />} />
              </Route>

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
