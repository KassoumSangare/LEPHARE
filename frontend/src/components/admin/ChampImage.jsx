import React, { useRef, useState } from 'react';
import { ImagePlus, Trash2, RotateCcw } from 'lucide-react';

// Taille d'impression d'un logo : au-delà, l'image est réduite avant l'envoi (poids < 600 Ko)
const LARGEUR_MAX = 900;
const HAUTEUR_MAX = 450;

/** Image choisie -> data URL réduite (PNG si transparente ou légère, sinon JPEG). */
const preparerImage = (fichier) => new Promise((resolve, reject) => {
  if (!/^image\/(png|jpeg|gif|webp|svg\+xml)$/.test(fichier.type)) {
    reject(new Error('Format non pris en charge : choisissez une image PNG, JPEG, GIF, WEBP ou SVG.'));
    return;
  }
  const lecteur = new FileReader();
  lecteur.onerror = () => reject(new Error('Lecture du fichier impossible.'));
  lecteur.onload = () => {
    const source = lecteur.result;
    if (fichier.type === 'image/svg+xml') {
      if (fichier.size > 300 * 1024) reject(new Error('Image SVG trop lourde (300 Ko au plus).'));
      else resolve(source);
      return;
    }
    const image = new Image();
    image.onerror = () => reject(new Error('Image illisible.'));
    image.onload = () => {
      const echelle = Math.min(1, LARGEUR_MAX / image.width, HAUTEUR_MAX / image.height);
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.width * echelle));
      canvas.height = Math.max(1, Math.round(image.height * echelle));
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      const png = canvas.toDataURL('image/png');
      if (png.length < 350 * 1024 || (fichier.type === 'image/png' && png.length < 700 * 1024)) {
        resolve(png);
        return;
      }
      // Image photographique : fond blanc et JPEG, bien plus léger
      const fond = document.createElement('canvas');
      fond.width = canvas.width;
      fond.height = canvas.height;
      const c2 = fond.getContext('2d');
      c2.fillStyle = '#ffffff';
      c2.fillRect(0, 0, fond.width, fond.height);
      c2.drawImage(canvas, 0, 0);
      resolve(fond.toDataURL('image/jpeg', 0.88));
    };
    image.src = source;
  };
  lecteur.readAsDataURL(fichier);
});

/**
 * Choix d'un logo : aperçu sur fond clair (comme à l'impression), remplacer, retirer, et revenir
 * au logo livré avec l'application quand `imageOrigine` est fournie.
 */
export const ChampImage = ({ libelle, aide, valeur, onChange, imageOrigine, hauteurApercu = 70, desactive }) => {
  const champ = useRef(null);
  const [erreur, setErreur] = useState('');
  const apercu = valeur || imageOrigine;

  const choisir = async (e) => {
    const fichier = e.target.files?.[0];
    e.target.value = '';
    if (!fichier) return;
    setErreur('');
    try {
      onChange(await preparerImage(fichier));
    } catch (err) {
      setErreur(err.message);
    }
  };

  return (
    <div className="form-group">
      {libelle && <label className="form-label">{libelle}</label>}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
        <div style={{ minWidth: 150, height: hauteurApercu + 16, padding: 8, borderRadius: 8, border: '1px dashed var(--border-medium)', background: '#ffffff', display: 'grid', placeItems: 'center' }}>
          {apercu
            ? <img src={apercu} alt={libelle || 'Logo'} style={{ maxHeight: hauteurApercu, maxWidth: 240, display: 'block' }} />
            : <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Aucune image</span>}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <input ref={champ} type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml" onChange={choisir} style={{ display: 'none' }} />
          <button type="button" className="btn btn-secondary" disabled={desactive} onClick={() => champ.current?.click()} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}>
            <ImagePlus size={14} /> {valeur ? 'Remplacer' : 'Choisir une image'}
          </button>
          {valeur && (
            <button type="button" className="btn btn-secondary" disabled={desactive} onClick={() => onChange('')} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}>
              {imageOrigine ? <><RotateCcw size={14} /> Revenir au logo d'origine</> : <><Trash2 size={14} /> Retirer</>}
            </button>
          )}
        </div>
      </div>
      {!valeur && imageOrigine && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Logo livré avec l'application.</span>}
      {aide && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{aide}</span>}
      {erreur && <span style={{ fontSize: '0.78rem', color: 'var(--accent-rose)' }}>{erreur}</span>}
    </div>
  );
};
