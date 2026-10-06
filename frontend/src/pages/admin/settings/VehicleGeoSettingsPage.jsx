import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Car } from 'lucide-react';
import { EnTeteParametrage } from '../../../components/admin/EnTeteParametrage';
import { TableBareme } from '../../../components/admin/TableBareme';

// Listes proposées à la saisie d'un véhicule (tables de la base). Les usages, rattachés aux
// catégories tarifaires, se règlent avec les offres ; les zones Voyage dans « Grilles Voyage ».
const LISTES = [
  {
    id: 'genres', libelle: 'Genres', route: 'genrevehicule', cle: 'IdGenre', nom: 'Genre de véhicule',
    colonnes: [
      { champ: 'CodeGenre', titre: 'Code', type: 'texte', requis: true, longueur: 10 },
      { champ: 'LibelleGenre', titre: 'Libellé', type: 'texte', requis: true, longueur: 60 },
    ],
  },
  {
    id: 'types', libelle: 'Types de véhicule', route: 'typevehicule', cle: 'id', nom: 'Type de véhicule',
    colonnes: [
      { champ: 'code_type', titre: 'Code', type: 'texte', requis: true, longueur: 10 },
      { champ: 'libelle_type', titre: 'Libellé', type: 'texte', requis: true, longueur: 100 },
    ],
  },
  {
    id: 'carrosseries', libelle: 'Carrosseries', route: 'carrosserie', cle: 'IdCarrosserie', nom: 'Carrosserie',
    colonnes: [{ champ: 'LibelleCarrosserie', titre: 'Libellé', type: 'texte', requis: true, longueur: 60 }],
  },
  {
    id: 'energies', libelle: 'Énergies', route: 'energie', cle: 'IdEnergie', nom: 'Énergie',
    colonnes: [
      { champ: 'CodeEnergie', titre: 'Code', type: 'texte', requis: true, longueur: 10 },
      { champ: 'Libelle', titre: 'Libellé', type: 'texte', requis: true, longueur: 50 },
    ],
  },
  {
    id: 'permis', libelle: 'Catégories de permis', route: 'categoriepermis', cle: 'id', nom: 'Catégorie de permis',
    colonnes: [{ champ: 'libelle', titre: 'Libellé', type: 'texte', requis: true, longueur: 50 }],
  },
];

export const VehicleGeoSettingsPage = () => {
  const [parametresUrl, setParametresUrl] = useSearchParams();
  const liste = LISTES.find((l) => l.id === parametresUrl.get('liste')) || LISTES[0];

  return (
    <div style={{ padding: '1.5rem' }}>
      <EnTeteParametrage
        icone={Car}
        titre="Listes véhicules"
        description="Genres, types, carrosseries, énergies et catégories de permis proposés à la saisie d'un véhicule ; les marques ont leur écran."
        usage="Une ligne déjà utilisée par des véhicules ne peut pas être supprimée : modifiez plutôt son libellé. Les zones Voyage se règlent dans « Grilles Voyage »."
      />
      <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.9rem', flexWrap: 'wrap' }}>
        {LISTES.map((l) => (
          <button key={l.id} type="button" onClick={() => setParametresUrl({ liste: l.id })} className={`btn ${liste.id === l.id ? 'btn-primary' : 'btn-secondary'}`}>{l.libelle}</button>
        ))}
      </div>
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <TableBareme key={liste.id} route={liste.route} cle={liste.cle} libelle={liste.nom} colonnes={liste.colonnes} />
      </div>
    </div>
  );
};

export default VehicleGeoSettingsPage;
