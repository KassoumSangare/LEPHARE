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
  HeartPulse,
  KeyRound,
  Landmark,
  LayoutDashboard,
  Layers,
  Car,
  Package,
  Percent,
  Plane,
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
      { to: '/admin/dashboard', droit: 'reporting.view', label: 'Tableau de bord', icon: LayoutDashboard, description: 'Production, encaissements, résultats et alertes de conformité du cabinet.' },
      { to: '/user/crm', droit: 'crm.view', label: 'Suivi commercial', icon: TrendingUp, description: 'Prospects et affaires en cours, étape par étape.' },
      { to: '/user/crm/360', droit: 'clients.view', label: 'Fiche client complète', icon: Users, description: "Tout sur un client : devis, contrats, sinistres et paiements." },
    ],
  },
  {
    id: 'cabinet',
    titre: 'Le cabinet',
    description: "Identité du cabinet, ce que reprennent les documents imprimés et les règles de gestion.",
    items: [
      { to: '/admin/settings/cabinet', droit: 'parametrage.update', label: 'Le cabinet & règles de gestion', icon: Landmark, description: "Coordonnées, logos et mentions des documents, règles de gestion (registre des devis, réduction Voyage, reversements) et délais d'avis d'échéance." },
    ],
  },
  {
    id: 'argent',
    titre: 'Argent & validations',
    description: "Ce que le cabinet reverse, ce qu'il perçoit et ce qui attend l'accord de la direction.",
    items: [
      { to: '/admin/remittances', droit: 'reversements.view', label: 'Reversements aux compagnies', icon: Building2, description: 'Primes encaissées reversées entières aux compagnies (Code CIMA : commission non déduite), bordereaux et paiements.' },
      { to: '/admin/commissions', droit: 'commissions.view', label: 'Commissions & apporteurs', icon: Coins, description: 'Réclamation des commissions sur les primes reversées, encaissement par chèque ou virement, états payées / non payées, apporteurs.' },
      { to: '/admin/approvals', droit: 'approbations.view', label: 'Demandes à valider', icon: CheckCheck, description: "Remises commerciales, annulations de quittances et autres dérogations qui attendent votre accord." },
    ],
  },
  {
    id: 'catalogue',
    titre: 'Catalogue : ce que nous vendons',
    description: 'Les compagnies, produits, offres, garanties, tarifs, taxes et commissions utilisés pour établir les devis.',
    items: [
      { to: '/admin/settings/companies', droit: 'parametrage.update', label: 'Compagnies partenaires', icon: Building2, description: "Les assureurs avec qui le cabinet travaille : coordonnées, logo et mentions de leurs documents, modèle d'attestation voyage, accès à leurs barèmes." },
      { to: '/admin/conventions', droit: 'parametrage.update', label: 'Conventions avec les compagnies', icon: FileSignature, description: "Les accords signés avec chaque compagnie : mandat d'encaissement, délais de reversement, plafonds de délégation." },
      { to: '/admin/settings/products', droit: 'parametrage.update', label: 'Produits', icon: Package, description: 'Automobile, Santé, IA, MRH… : onglet du registre des devis, formulaire de saisie, saisie ouverte ou fermée.' },
      { to: '/admin/settings/offres', droit: 'tarifs.view', label: 'Offres', icon: Boxes, description: 'Les formules proposées par compagnie et par catégorie, avec les garanties comprises et leurs franchises.' },
      { to: '/admin/settings/garanties-oreole', droit: 'tarifs.view', label: 'Garanties & sous-garanties', icon: Shield, description: "La liste de toutes les garanties utilisables dans les offres ; pour en rattacher une à une offre, voir « Offres »." },
      { to: '/admin/settings/tarifs', droit: 'tarifs.view', label: 'Accessoires', icon: Receipt, description: 'Frais de dossier par tranche de prime nette : ceux de chaque compagnie (par produit) et la part du cabinet.' },
      { to: '/admin/settings/grilles-voyage', droit: 'tarifs.view', label: 'Grilles Voyage', icon: Plane, description: 'Primes, accessoires et taxes Voyage par compagnie, offres proposées par zone et zone de chaque pays de destination.' },
      { to: '/admin/settings/dommages', droit: 'tarifs.view', label: 'Réglages Dommages', icon: Layers, description: 'Caution, Tous Risques Informatiques, Chantiers, Bris de Machines… : catégories proposées, description du risque demandée, garanties par compagnie avec taux proposé, franchise et taxe.' },
      { to: '/admin/settings/sante', droit: 'tarifs.view', label: 'Réglages Santé MINENE', icon: HeartPulse, description: "MINENE SANTÉ (Santé, IA et RC chef de famille) : prime et barème de soins de chaque formule, surprimes et âges, capitaux IA et RC, délais de carence, clause d'ajustement et répartition de la prime." },
      { to: '/admin/settings/taxes', droit: 'tarifs.view', label: 'Taxes', icon: Percent, description: "Taux de taxe sur les contrats d'assurance, par produit et par garantie, avec leur période de validité." },
      { to: '/admin/settings/commissions-baremes', droit: 'tarifs.view', label: 'Taux de commission', icon: Coins, description: 'Commission du cabinet par compagnie et par produit, avec sa période de validité.' },
    ],
  },
  {
    id: 'auto',
    titre: 'Réglages Automobile',
    description: 'Les paramètres propres aux devis Automobile.',
    items: [
      { to: '/admin/settings/marques', droit: 'parametrage.update', label: 'Marques de véhicules', icon: Tag, description: 'Liste des marques proposées lors de la saisie du véhicule.' },
      { to: '/admin/settings/flotte', droit: 'tarifs.view', label: 'Réductions flotte', icon: Truck, description: "Remise accordée automatiquement selon le nombre de véhicules d'un devis flotte, par compagnie." },
      { to: '/admin/settings/securite-routiere', droit: 'tarifs.view', label: 'Sécurité routière', icon: TrafficCone, description: 'Formules de la garantie des personnes transportées, par compagnie : capitaux et prime nette.' },
    ],
  },
  {
    id: 'listes',
    titre: 'Listes de référence',
    description: 'Les listes proposées dans les formulaires (clients, véhicules, zones).',
    items: [
      { to: '/admin/settings/vehicle-geo', droit: 'parametrage.update', label: 'Listes véhicules', icon: Car, description: "Genres, types, carrosseries, énergies et catégories de permis proposés à la saisie d'un véhicule." },
      { to: '/admin/settings/professions', droit: 'parametrage.update', label: 'Professions', icon: Briefcase, description: 'Professions proposées sur les fiches clients.' },
      { to: '/admin/settings/secteurs-activite', droit: 'parametrage.update', label: "Secteurs d'activité", icon: Factory, description: "Secteurs d'activité des entreprises clientes." },
      { to: '/admin/settings/types-souscripteur', droit: 'parametrage.update', label: 'Types de souscripteur', icon: UserPlus, description: 'Personne physique, entreprise, association…' },
      { to: '/admin/settings/types-assure', droit: 'parametrage.update', label: "Types d'assuré", icon: UserCheck, description: "Catégories de personnes ou de biens assurés." },
    ],
  },
  {
    id: 'rapports',
    titre: 'Rapports & contrôle',
    description: 'États à produire, suivi de la conformité, sinistres et documents.',
    items: [
      { to: '/admin/reporting/cima', droit: 'reporting.view', label: 'États réglementaires CIMA', icon: FileSpreadsheet, description: "États officiels pour l'autorité de contrôle, la DGTCP et les commissaires aux comptes." },
      { to: '/admin/reporting/emissions', droit: 'reporting.view', label: 'Bordereau des émissions', icon: ScrollText, description: 'Polices émises par compagnie, par branche et par client.' },
      { to: '/admin/reporting/etats-decisionnels', droit: 'reporting.view', label: 'États de gestion', icon: BarChart3, description: 'Tableaux de suivi : émissions, commissions, encaissements.' },
      { to: '/admin/compliance', droit: 'audit.view', label: 'Conformité & audit', icon: BadgeCheck, description: "Agrément, garantie financière de 50 M FCFA et journal de toutes les opérations." },
      { to: '/user/claims', droit: 'sinistres.view', label: 'Suivi des sinistres', icon: AlertTriangle, description: 'Sinistres déclarés et gérés pour le compte des compagnies.' },
      { to: '/user/documents', droit: 'documents.view', label: 'Documents (GED)', icon: FolderOpen, description: 'Pièces justificatives classées par client et par contrat.' },
      { to: '/user/archives', droit: 'devis.view', label: 'Archives', icon: Archive, description: 'Devis et contrats archivés.' },
    ],
  },
  {
    id: 'acces',
    titre: 'Utilisateurs & sécurité',
    description: "Qui peut se connecter, ce que chacun a le droit de faire, et la trace de tout ce qui est fait.",
    items: [
      { to: '/admin/users', droit: 'users.view', label: 'Utilisateurs', icon: Users, description: 'Comptes, rôles attribués, droits effectifs, activation, mot de passe provisoire et activité récente.' },
      { to: '/admin/profiles', droit: 'roles.view', label: 'Rôles', icon: UserCog, description: 'Rôles (Direction, Gestionnaire, Agent de saisie…) : création, activation et droits accordés par module.' },
      { to: '/admin/roles-permissions', droit: 'roles.view', label: 'Droits', icon: KeyRound, description: "Catalogue des actions contrôlées par module, rôles qui les accordent, motif obligatoire et séparation des tâches." },
      { to: '/admin/audit', droit: 'audit.view', label: "Journal d'audit", icon: ScrollText, description: "Qui a fait quoi, quand, sur quel objet, avec quel résultat et quelles valeurs avant / après." },
    ],
  },
];

// Premier écran d'administration permis par les droits (peut : fonction de AuthContext)
export const premierEcranAdmin = (peut) => {
  const ecran = ADMIN_MENU.flatMap((g) => g.items).find((i) => i.to.startsWith('/admin') && i.to !== '/admin/guide' && peut(i.droit));
  return ecran ? ecran.to : '/admin/guide';
};

// Un écran est actif si l'adresse courante est la sienne (ou une de ses sous-pages)
export const estActif = (pathname, to) => pathname === to || pathname.startsWith(`${to}/`);
