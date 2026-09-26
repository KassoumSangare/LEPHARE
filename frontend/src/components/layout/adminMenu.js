/**
 * Plan de l'espace Administration : une seule définition, utilisée par le menu latéral
 * et par la page « Guide de l'administration ». Les groupes suivent ce que l'on veut faire,
 * avec des libellés simples et une phrase d'explication par écran.
 */
import {
  Archive,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  Boxes,
  Briefcase,
  Building2,
  CheckCheck,
  Coins,
  Compass,
  Factory,
  FileSignature,
  FileSpreadsheet,
  FolderOpen,
  KeyRound,
  LayoutDashboard,
  MapPin,
  Package,
  Percent,
  Receipt,
  ScrollText,
  Shield,
  Tag,
  TrafficCone,
  TrendingUp,
  Truck,
  UserCheck,
  UserCog,
  UserPlus,
  Users,
} from 'lucide-react';

export const ADMIN_MENU = [
  {
    id: 'vue',
    titre: "Vue d'ensemble",
    description: 'Les chiffres du cabinet et le suivi des clients.',
    items: [
      { to: '/admin/guide', label: "Guide de l'administration", icon: Compass, description: "Le plan de cet espace : ce que contient chaque écran et où trouver un réglage." },
      { to: '/admin/dashboard', label: 'Tableau de bord', icon: LayoutDashboard, description: 'Production, encaissements, résultats et alertes de conformité du cabinet.' },
      { to: '/user/crm', label: 'Suivi commercial', icon: TrendingUp, description: 'Prospects et affaires en cours, étape par étape.' },
      { to: '/user/crm/360', label: 'Fiche client complète', icon: Users, description: "Tout sur un client : devis, contrats, sinistres et paiements." },
    ],
  },
  {
    id: 'argent',
    titre: 'Argent & validations',
    description: "Ce que le cabinet reverse, ce qu'il perçoit et ce qui attend l'accord de la direction.",
    items: [
      { to: '/admin/remittances', label: 'Reversements aux compagnies', icon: Building2, description: 'Primes encaissées à reverser aux compagnies, commissions déduites, sous 30 jours (règle CIMA).' },
      { to: '/admin/commissions', label: 'Commissions & apporteurs', icon: Coins, description: 'Commissions gagnées par le cabinet et rétrocessions versées aux apporteurs.' },
      { to: '/admin/approvals', label: 'Demandes à valider', icon: CheckCheck, description: "Remises commerciales, annulations de quittances et autres dérogations qui attendent votre accord." },
    ],
  },
  {
    id: 'catalogue',
    titre: 'Catalogue : ce que nous vendons',
    description: 'Les compagnies, produits, offres, garanties, tarifs, taxes et commissions utilisés pour établir les devis.',
    items: [
      { to: '/admin/settings/companies', label: 'Compagnies partenaires', icon: Building2, description: 'Les assureurs avec qui le cabinet travaille : agréments, codes ASACI, modalités de reversement.' },
      { to: '/admin/conventions', label: 'Conventions avec les compagnies', icon: FileSignature, description: "Les accords signés avec chaque compagnie : mandat d'encaissement, délais de reversement, plafonds de délégation." },
      { to: '/admin/settings/products', label: 'Produits (branches)', icon: Package, description: "Automobile, Santé, IA, MRH… ; l'onglet « Garanties » donne leurs garanties de référence." },
      { to: '/admin/settings/offres', label: 'Offres', icon: Boxes, description: 'Les formules proposées par compagnie et par catégorie, avec les garanties comprises et leurs franchises.' },
      { to: '/admin/settings/garanties-oreole', label: 'Garanties & sous-garanties', icon: Shield, description: "La liste de toutes les garanties utilisables dans les offres ; pour en rattacher une à une offre, voir « Offres »." },
      { to: '/admin/settings/tarifs', label: 'Tarifs & accessoires', icon: Receipt, description: 'Catégories tarifaires, barèmes de calcul, coefficients de durée et frais de gestion.' },
      { to: '/admin/settings/taxes', label: 'Taxes', icon: Percent, description: "Taux de taxe sur les contrats d'assurance, fonds de garantie automobile (FGA) et exonérations." },
      { to: '/admin/settings/commissions-baremes', label: 'Taux de commission', icon: Coins, description: 'Taux de commission du cabinet par branche et par compagnie.' },
    ],
  },
  {
    id: 'auto',
    titre: 'Réglages Automobile',
    description: 'Les paramètres propres aux devis Automobile.',
    items: [
      { to: '/admin/settings/marques', label: 'Marques de véhicules', icon: Tag, description: 'Liste des marques proposées lors de la saisie du véhicule.' },
      { to: '/admin/settings/flotte', label: 'Réductions flotte', icon: Truck, description: "Remise accordée automatiquement selon le nombre de véhicules d'un même client." },
      { to: '/admin/settings/securite-routiere', label: 'Sécurité routière', icon: TrafficCone, description: 'Formules de la garantie des personnes transportées : capitaux et prime par place.' },
    ],
  },
  {
    id: 'listes',
    titre: 'Listes de référence',
    description: 'Les listes proposées dans les formulaires (clients, véhicules, zones).',
    items: [
      { to: '/admin/settings/vehicle-geo', label: 'Véhicules, zones, voyage & transport', icon: MapPin, description: 'Genres de véhicules, zones géographiques, grilles Voyage et Transport.' },
      { to: '/admin/settings/professions', label: 'Professions', icon: Briefcase, description: 'Professions proposées sur les fiches clients.' },
      { to: '/admin/settings/secteurs-activite', label: "Secteurs d'activité", icon: Factory, description: "Secteurs d'activité des entreprises clientes." },
      { to: '/admin/settings/types-souscripteur', label: 'Types de souscripteur', icon: UserPlus, description: 'Personne physique, entreprise, association…' },
      { to: '/admin/settings/types-assure', label: "Types d'assuré", icon: UserCheck, description: "Catégories de personnes ou de biens assurés." },
    ],
  },
  {
    id: 'rapports',
    titre: 'Rapports & contrôle',
    description: 'États à produire, suivi de la conformité, sinistres et documents.',
    items: [
      { to: '/admin/reporting/cima', label: 'États réglementaires CIMA', icon: FileSpreadsheet, description: "États officiels pour l'autorité de contrôle, la DGTCP et les commissaires aux comptes." },
      { to: '/admin/reporting/emissions', label: 'Bordereau des émissions', icon: ScrollText, description: 'Polices émises par compagnie, par branche et par client.' },
      { to: '/admin/reporting/etats-decisionnels', label: 'États de gestion', icon: BarChart3, description: 'Tableaux de suivi : émissions, commissions, encaissements.' },
      { to: '/admin/compliance', label: 'Conformité & audit', icon: BadgeCheck, description: "Agrément, garantie financière de 50 M FCFA et journal de toutes les opérations." },
      { to: '/user/claims', label: 'Suivi des sinistres', icon: AlertTriangle, description: 'Sinistres déclarés et gérés pour le compte des compagnies.' },
      { to: '/user/documents', label: 'Documents (GED)', icon: FolderOpen, description: 'Pièces justificatives classées par client et par contrat.' },
      { to: '/user/archives', label: 'Archives', icon: Archive, description: 'Devis et contrats archivés.' },
    ],
  },
  {
    id: 'acces',
    titre: 'Utilisateurs & accès',
    description: 'Qui peut se connecter et ce que chacun a le droit de faire.',
    items: [
      { to: '/admin/users', label: 'Comptes utilisateurs', icon: Users, description: 'Créer un compte, lui attribuer un profil, réinitialiser un mot de passe.' },
      { to: '/admin/profiles', label: 'Profils', icon: UserCog, description: 'Les profils types (direction, production, caisse…), leurs droits et leurs plafonds de dérogation.' },
      { to: '/admin/roles-permissions', label: "Droits d'accès détaillés", icon: KeyRound, description: 'Le tableau complet des droits, opération par opération.' },
    ],
  },
];

// Un écran est actif si l'adresse courante est la sienne (ou une de ses sous-pages)
export const estActif = (pathname, to) => pathname === to || pathname.startsWith(`${to}/`);
