import React from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { Contact } from 'lucide-react';
import { RechercheClient } from '../../../components/common/RechercheClient';

// « Fiche client complète » : ouvre le dossier 360° réel du client (ClientDetailPage, alimenté par
// /api/client/<id>/dossier/, filtré en base par idclient). L'ancienne vue chargeait les listes de
// contrats et devis tronquées à 200 lignes puis filtrait par nom, avec un journal et des documents
// inventés.
export const Customer360Page = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const clientId = searchParams.get('clientId');

  if (clientId) return <Navigate to={`/user/clients/${clientId}`} replace />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: 720 }}>
      <div>
        <h1 className="title-xl" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <Contact size={26} color="#94a3b8" />
          Fiche client complète
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Recherchez un client pour ouvrir son dossier 360° : identité, synthèse, devis en cours,
          contrats, quittances et encaissements, lus directement en base.
        </p>
      </div>
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <RechercheClient
          label="Client"
          personne={null}
          onChoisir={(p) => { if (p?.IdClient) navigate(`/user/clients/${p.IdClient}`); }}
        />
      </div>
    </div>
  );
};

export default Customer360Page;
