"""
Données de démonstration du module institutionnel (conventions, sinistres délégués, GED, journal,
quittances CIMA, bordereaux de reversement).

Elles ne sont plus créées par les consultations de l'API (une table vide se remplissait au premier
GET, y compris en production après un nettoyage) : seule la commande explicite
« python manage.py semer_demo_institutionnel » les insère, et seulement dans une table vide.
"""

import datetime

from .models import AuditLogCima, BordereauReversement, ConventionAssureur, DocumentGED, QuittanceCima, SinistreDelegue


def semer_donnees_demo():
    """Insère les données de démonstration dans les tables vides ; renvoie les tables remplies."""
    remplies = []

    if ConventionAssureur.objects.count() == 0:
        remplies.append("ConventionAssureur")
        ConventionAssureur.objects.bulk_create([
            ConventionAssureur(
                code_convention="CNV-2026-001",
                compagnie="NSIA Assurances Côte d'Ivoire",
                code_partenaire="NSIA-CRT-048",
                delai_reversement_jours=30,
                plafond_delegation_sinistre=5000000,
                encaissement_delegue=True,
                statut="Actif",
                date_effet=datetime.date(2026, 1, 1),
                date_renouvellement=datetime.date(2026, 12, 31),
                commissions_branches={"automobile": 12.5, "mrh": 15.0, "sante": 10.0, "rc": 14.0},
                participation_beneficiaire={"active": True, "taux": "15%", "seuil_sp": "60%"}
            ),
            ConventionAssureur(
                code_convention="CNV-2026-002",
                compagnie="SUNU Assurances CI",
                code_partenaire="SUNU-PART-112",
                delai_reversement_jours=30,
                plafond_delegation_sinistre=3500000,
                encaissement_delegue=True,
                statut="Actif",
                date_effet=datetime.date(2026, 1, 1),
                date_renouvellement=datetime.date(2026, 12, 31),
                commissions_branches={"automobile": 11.0, "mrh": 14.0, "sante": 12.0, "rc": 12.5},
                participation_beneficiaire={"active": True, "taux": "12%", "seuil_sp": "65%"}
            ),
            ConventionAssureur(
                code_convention="CNV-2026-003",
                compagnie="SANLAM Assurance",
                code_partenaire="SANLAM-AGY-009",
                delai_reversement_jours=30,
                plafond_delegation_sinistre=7000000,
                encaissement_delegue=True,
                statut="Actif",
                date_effet=datetime.date(2026, 1, 1),
                date_renouvellement=datetime.date(2026, 12, 31),
                commissions_branches={"automobile": 13.0, "mrh": 16.0, "sante": 11.5, "rc": 15.0},
                participation_beneficiaire={"active": True, "taux": "18%", "seuil_sp": "55%"}
            ),
            ConventionAssureur(
                code_convention="CNV-2026-004",
                compagnie="ALLIANZ Côte d'Ivoire",
                code_partenaire="ALLIANZ-LEPHARE-01",
                delai_reversement_jours=30,
                plafond_delegation_sinistre=5000000,
                encaissement_delegue=True,
                statut="Actif",
                date_effet=datetime.date(2026, 1, 1),
                date_renouvellement=datetime.date(2026, 12, 31),
                commissions_branches={"automobile": 12.0, "mrh": 15.0, "sante": 10.0, "rc": 13.5},
                participation_beneficiaire={"active": False, "taux": "0%", "seuil_sp": "70%"}
            )
        ])

    if SinistreDelegue.objects.count() == 0:
        remplies.append("SinistreDelegue")
        SinistreDelegue.objects.bulk_create([
            SinistreDelegue(
                numero_sinistre="SIN-2026-00125",
                police_num="POL-2026-001",
                assure_nom="KOUAME Jean-Baptiste",
                compagnie="NSIA Assurances Côte d'Ivoire",
                nature="Accident de la circulation - Choc arrière",
                date_survenance=datetime.date(2026, 8, 28),
                date_declaration=datetime.date(2026, 8, 30),
                lieu="Abidjan Boulevard VGE",
                montant_reclame=1850000,
                montant_indemnise=1650000,
                statut="Réglé",
                delegation_respectee=True,
                expert_assigne="Cabinet d'Expertise Automobile CI",
                pieces_justificatives=[
                    {"nom": "Déclaration signée", "recu": True},
                    {"nom": "Constat amiable", "recu": True},
                    {"nom": "Permis de conduire", "recu": True},
                    {"nom": "Devis de réparation", "recu": True},
                    {"nom": "Rapport expertise", "recu": True},
                    {"nom": "Quittance d'indemnité", "recu": True}
                ],
                recours_info={"compagnie_adverse": "SUNU Assurances CI", "montant_recours": 1650000, "statut": "Recours encaissé"},
                historique_evenements=[
                    {"date": "2026-08-30", "action": "Déclaration enregistrée"},
                    {"date": "2026-09-02", "action": "Rapport expertise chiffré à 1 650 000 FCFA"},
                    {"date": "2026-09-04", "action": "Règlement sous mandat de délégation approuvé et viré"}
                ]
            ),
            SinistreDelegue(
                numero_sinistre="SIN-2026-00126",
                police_num="POL-2026-002",
                assure_nom="SOCIETE IVOIRIENNE DE DISTRIBUTION",
                compagnie="SANLAM Assurance",
                nature="Incendie local technique et entrepôt",
                date_survenance=datetime.date(2026, 9, 1),
                date_declaration=datetime.date(2026, 9, 2),
                lieu="Zone Industrielle de Yopougon",
                montant_reclame=8500000,
                montant_indemnise=0,
                statut="En attente validation",
                delegation_respectee=False,
                expert_assigne="Bureau Veritas Sinistres CI",
                pieces_justificatives=[
                    {"nom": "Déclaration signée", "recu": True},
                    {"nom": "Rapport sapeurs-pompiers", "recu": True},
                    {"nom": "Factures matériels endommagés", "recu": True},
                    {"nom": "Rapport contradictoire", "recu": False},
                    {"nom": "Mandat compagnie requis (> 7M)", "recu": False}
                ],
                recours_info={"statut": "Sans tiers identifié"},
                historique_evenements=[
                    {"date": "2026-09-02", "action": "Déclaration reçue"},
                    {"date": "2026-09-03", "action": "Montant supérieur au plafond de délégation (7 000 000 FCFA) : saisine de SANLAM pour mandat spécial"}
                ]
            ),
            SinistreDelegue(
                numero_sinistre="SIN-2026-00127",
                police_num="POL-2026-003",
                assure_nom="BAMBA Mariam",
                compagnie="SUNU Assurances CI",
                nature="Dégât des eaux appartement Cocody",
                date_survenance=datetime.date(2026, 9, 3),
                date_declaration=datetime.date(2026, 9, 4),
                lieu="Cocody Riviera Golf",
                montant_reclame=850000,
                montant_indemnise=0,
                statut="Expertise en cours",
                delegation_respectee=True,
                expert_assigne="Cabinet CIMA Expertises",
                pieces_justificatives=[
                    {"nom": "Déclaration signée", "recu": True},
                    {"nom": "Photos des dommages", "recu": True},
                    {"nom": "Devis plomberie", "recu": True},
                    {"nom": "Rapport expertise", "recu": False}
                ],
                recours_info={"compagnie_adverse": "NSIA Assurances CI", "montant_recours": 850000, "statut": "En attente rapport"},
                historique_evenements=[
                    {"date": "2026-09-04", "action": "Dossier ouvert et expert mandaté sous 24h"}
                ]
            )
        ])

    if DocumentGED.objects.count() == 0:
        remplies.append("DocumentGED")
        DocumentGED.objects.bulk_create([
            DocumentGED(
                reference="DOC-2026-001",
                titre="Police Signée - Flotte Automobile SIFCA",
                categorie="Contrat",
                type_mime="application/pdf",
                taille="2.4 MB",
                entite_type="contrat",
                entite_id="POL-2026-001",
                statut_validation="Validé",
                auteur="Direction Technique LE PHARE"
            ),
            DocumentGED(
                reference="DOC-2026-002",
                titre="Convention Cadre Gestion Déléguée NSIA 2026",
                categorie="Convention",
                type_mime="application/pdf",
                taille="4.1 MB",
                entite_type="convention",
                entite_id="CNV-2026-001",
                statut_validation="Validé",
                auteur="Direction Générale LE PHARE"
            ),
            DocumentGED(
                reference="DOC-2026-003",
                titre="Rapport d'expertise contradictoire SIN-00125",
                categorie="Sinistre",
                type_mime="application/pdf",
                taille="1.8 MB",
                entite_type="sinistre",
                entite_id="SIN-2026-00125",
                statut_validation="Validé",
                auteur="Cabinet d'Expertise Automobile CI"
            ),
            DocumentGED(
                reference="DOC-2026-004",
                titre="Attestation Caution Financière 50M FCFA SGCI",
                categorie="KYC",
                type_mime="application/pdf",
                taille="1.1 MB",
                entite_type="audit",
                entite_id="CAUTION-SGCI-2026",
                statut_validation="Validé",
                auteur="SGCI Direction Grandes Entreprises"
            )
        ])

    if AuditLogCima.objects.count() == 0:
        remplies.append("AuditLogCima")
        AuditLogCima.objects.bulk_create([
            AuditLogCima(
                type_operation="ENCAISSEMENT",
                description="Encaissement prime annuelle 450 000 FCFA chèque certifié ECOBANK (Reçu N° REC-2026-001)",
                auteur="Koffi Serge",
                statut_conformite="CONFORME",
                reference_reglementaire="CIMA Art. 13 - Paiement préalable à la délivrance de l'attestation",
                details_json={"police": "POL-2026-001", "montant": 450000}
            ),
            AuditLogCima(
                type_operation="REVERSEMENT",
                description="Ordre de reversement net de commissions vers NSIA sous délai de 22 jours (conforme max 30 jours)",
                auteur="Direction Financière LE PHARE",
                statut_conformite="CONFORME",
                reference_reglementaire="Convention Assureur Art. 7 & CIMA",
                details_json={"compagnie": "NSIA Assurances", "montant": 12850000}
            ),
            AuditLogCima(
                type_operation="SINISTRE_REGLEMENT",
                description="Ordonnancement règlement sinistre SIN-00125 (1 650 000 FCFA) conforme au plafond de délégation (5 000 000 FCFA)",
                auteur="Amina Diallo",
                statut_conformite="CONFORME",
                reference_reglementaire="Mandat de Gestion Déléguée Sinistres",
                details_json={"sinistre": "SIN-2026-00125", "indemnite": 1650000}
            )
        ])

    if QuittanceCima.objects.count() == 0:
        remplies.append("QuittanceCima")
        QuittanceCima.objects.bulk_create([
            QuittanceCima(
                numero_quittance="QUIT-CIMA-2026-001",
                police_num="POL-2026-001",
                souscripteur="KOUAME Jean-Baptiste",
                compagnie="NSIA Assurances",
                branche="Automobile",
                montant_encaisse=450000,
                mode_paiement="CHEQUE",
                reference_paiement="CHQ-ECOBANK-998812",
                emetteur="Caisse Principale LE PHARE"
            ),
            QuittanceCima(
                numero_quittance="QUIT-CIMA-2026-002",
                police_num="POL-2026-002",
                souscripteur="SOCIETE IVOIRIENNE DE DISTRIBUTION",
                compagnie="SANLAM Assurance",
                branche="IARD",
                montant_encaisse=1250000,
                mode_paiement="VIREMENT",
                reference_paiement="VIR-SGCI-20260901",
                emetteur="Caisse Principale LE PHARE"
            )
        ])

    if BordereauReversement.objects.count() == 0:
        remplies.append("BordereauReversement")
        BordereauReversement.objects.bulk_create([
            BordereauReversement(
                reference="REV-NSIA-2026-09",
                compagnie="NSIA Assurances",
                nombre_polices=38,
                montant_primes=14500000,
                commissions_deduites=1740000,
                net_a_reverser=12760000,
                date_echeance_30j=datetime.date.today() + datetime.timedelta(days=12),
                statut="Validé",
                ordre_virement_ref="OV-SGCI-2026-0012"
            ),
            BordereauReversement(
                reference="REV-SUNU-2026-09",
                compagnie="SUNU Assurances",
                nombre_polices=24,
                montant_primes=9800000,
                commissions_deduites=1176000,
                net_a_reverser=8624000,
                date_echeance_30j=datetime.date.today() + datetime.timedelta(days=4),
                statut="En attente validation",
                ordre_virement_ref=""
            ),
            BordereauReversement(
                reference="REV-SANLAM-2026-09",
                compagnie="SANLAM Assurances",
                nombre_polices=15,
                montant_primes=4200000,
                commissions_deduites=504000,
                net_a_reverser=3696000,
                date_echeance_30j=datetime.date.today() + datetime.timedelta(days=18),
                statut="En attente validation",
                ordre_virement_ref=""
            )
        ])
    return remplies
