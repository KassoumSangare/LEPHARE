import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Receipt, Building2, Briefcase } from 'lucide-react';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { TableBareme } from '../../../components/admin/TableBareme';

// Accessoires (frais de dossier) par tranche de prime nette : celui de la compagnie, par produit
// (stdaccessoire, fn_get_accessoire) et la part du cabinet (stdaccessoirecourtierparcompagnie,
// fn_get_accessoire_intermediaire). Colonne « montantforfait » de stdaccessoire non lue par le calcul.

const trancheCoherente = (min, max) => (Number(min) > Number(max) ? 'La prime minimum de la tranche doit être inférieure ou égale à la prime maximum.' : null);
const chevauchement = (ligne, autres, memeBareme, champMin, champMax) => {
  const autre = autres.find((l) => memeBareme(l) && Number(l[champMin]) <= Number(ligne[champMax]) && Number(ligne[champMin]) <= Number(l[champMax]));
  return autre ? `Cette tranche chevauche celle de ${Number(autre[champMin]).toLocaleString('fr-FR')} à ${Number(autre[champMax]).toLocaleString('fr-FR')} F.` : null;
};

const ONGLETS = [
  {
    id: 'compagnie',
    libelle: 'Accessoires de la compagnie',
    icone: Building2,
    aide: "Frais de dossier facturés sur la quittance selon la tranche de prime nette du devis, par compagnie et par produit. Une compagnie sans tranche pour un produit n'applique aucun accessoire.",
    props: {
      route: 'accessoire',
      cle: 'id',
      libelle: "Tranche d'accessoires",
      colonnes: [
        { champ: 'compagnie', titre: 'Compagnie', type: 'compagnie', requis: true, filtre: true },
        { champ: 'produit', titre: 'Produit', type: 'produit', requis: true, filtre: true },
        { champ: 'primemin', titre: 'Prime nette de', type: 'montant', requis: true, min: 0 },
        { champ: 'primemax', titre: 'Prime nette à', type: 'montant', requis: true, min: 0 },
        { champ: 'accessoires', titre: 'Accessoires', type: 'montant', requis: true, min: 0 },
      ],
      controle: (ligne, autres) => trancheCoherente(ligne.primemin, ligne.primemax)
        || chevauchement(ligne, autres, (l) => Number(l.compagnie) === Number(ligne.compagnie) && Number(l.produit) === Number(ligne.produit), 'primemin', 'primemax'),
      tri: (a, b) => Number(a.compagnie) - Number(b.compagnie) || Number(a.produit) - Number(b.produit) || Number(a.primemin) - Number(b.primemin),
    },
  },
  {
    id: 'courtier',
    libelle: 'Accessoires du cabinet',
    icone: Briefcase,
    aide: "Part des accessoires revenant au cabinet (intermédiaire), par compagnie et par tranche de prime nette, tous produits confondus.",
    props: {
      route: 'accessoirecourtier',
      cle: 'IdAccessoireCourtier',
      libelle: "Tranche d'accessoires du cabinet",
      colonnes: [
        { champ: 'IdCompagnie', titre: 'Compagnie', type: 'compagnie', requis: true, filtre: true },
        { champ: 'PrimeMin', titre: 'Prime nette de', type: 'montant', requis: true, min: 0 },
        { champ: 'PrimeMax', titre: 'Prime nette à', type: 'montant', requis: true, min: 0 },
        { champ: 'Accessoires', titre: 'Accessoires', type: 'montant', requis: true, min: 0 },
        { champ: 'Forfait', titre: 'Forfait', type: 'montant', requis: true, min: 0 },
      ],
      valeursParDefaut: { Forfait: 0 },
      controle: (ligne, autres) => trancheCoherente(ligne.PrimeMin, ligne.PrimeMax)
        || chevauchement(ligne, autres, (l) => Number(l.IdCompagnie) === Number(ligne.IdCompagnie), 'PrimeMin', 'PrimeMax'),
      tri: (a, b) => Number(a.IdCompagnie) - Number(b.IdCompagnie) || Number(a.PrimeMin) - Number(b.PrimeMin),
    },
  },
];

export const CatalogTarifsPage = () => {
  const [parametresUrl] = useSearchParams();
  const [onglet, setOnglet] = useState(parametresUrl.get('onglet') === 'courtier' ? 'courtier' : 'compagnie');
  const actif = ONGLETS.find((o) => o.id === onglet);

  return (
    <div style={{ padding: '1.5rem' }}>
      <EnTeteParametrage
        icone={Receipt}
        titre="Accessoires"
        description="Frais de dossier ajoutés à la prime nette, par tranche de prime : ceux de la compagnie et la part du cabinet."
        usage="Lus par le calcul de chaque devis (tranche de la prime nette du devis). Les catégories et tarifs des offres se règlent dans « Offres »."
      />
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.9rem', flexWrap: 'wrap' }}>
        {ONGLETS.map((o) => (
          <button key={o.id} type="button" onClick={() => setOnglet(o.id)} className={`btn ${onglet === o.id ? 'btn-primary' : 'btn-secondary'}`} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <o.icone size={15} /> {o.libelle}
          </button>
        ))}
      </div>
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 0 }}>{actif.aide}</p>
        <TableBareme key={actif.id} {...actif.props} />
      </div>
    </div>
  );
};

export default CatalogTarifsPage;
