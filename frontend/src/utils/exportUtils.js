/**
 * UTILS D'EXPORTATION MULTI-FORMATS LE PHARE (PDF, EXCEL, CSV, XML)
 * Conforme aux exigences réglementaires du Code CIMA et de la comptabilité générale.
 */

export const downloadBlob = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 300);
};

/**
 * Export CSV standard avec BOM UTF-8 pour ouverture parfaite dans Microsoft Excel
 */
export const exportToCsv = ({ filename, title, metadata = {}, headers, rows, totals }) => {
  let csv = '\uFEFF'; // BOM UTF-8
  if (title) {
    csv += `"${title.replace(/"/g, '""')}"\n`;
  }
  Object.entries(metadata).forEach(([k, v]) => {
    csv += `"${k}";"${String(v).replace(/"/g, '""')}"\n`;
  });
  csv += '\n';

  csv += headers.map((h) => `"${String(h).replace(/"/g, '""')}"`).join(';') + '\n';

  rows.forEach((row) => {
    csv += row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(';') + '\n';
  });

  if (totals && totals.length > 0) {
    csv += '\n';
    csv += totals.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(';') + '\n';
  }

  const cleanName = filename.endsWith('.csv') ? filename : `${filename}.csv`;
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, cleanName);
};

/**
 * Export Excel stylisé (.xls / .xlsx) avec formatage monétaire, totaux et en-tête officiel
 */
export const exportToExcel = ({ filename, title, subtitle, metadata = {}, headers, rows, totals }) => {
  const metaRows = Object.entries(metadata)
    .map(([k, v]) => `<tr><td style="font-weight:bold;color:#475569;padding:3px;">${k} :</td><td colspan="${headers.length - 1}" style="padding:3px;">${v}</td></tr>`)
    .join('');

  const headerCells = headers
    .map((h) => `<th style="background:#1e293b;color:#ffffff;font-weight:bold;padding:8px 10px;border:1px solid #cbd5e1;text-align:left;">${h}</th>`)
    .join('');

  const bodyRows = rows
    .map((row, idx) => {
      const bg = idx % 2 === 0 ? '#ffffff' : '#f8fafc';
      const cells = row
        .map((cell, colIdx) => {
          const isNum = typeof cell === 'number' || (typeof cell === 'string' && /^[0-9\s]+(\s*F(CFA)?)?$/.test(cell.trim()));
          const align = colIdx > 0 && isNum ? 'right' : 'left';
          return `<td style="padding:6px 10px;border:1px solid #cbd5e1;text-align:${align};">${cell ?? ''}</td>`;
        })
        .join('');
      return `<tr style="background:${bg};">${cells}</tr>`;
    })
    .join('');

  const totalRowHtml = totals && totals.length > 0
    ? `<tr style="background:#e2e8f0;font-weight:bold;border-top:2px solid #0f172a;border-bottom:2px solid #0f172a;">
        ${totals.map((t, idx) => `<td style="padding:8px 10px;border:1px solid #94a3b8;text-align:${idx > 0 ? 'right' : 'left'};">${t ?? ''}</td>`).join('')}
       </tr>`
    : '';

  const html = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
      <head>
        <!--[if gte mso 9]>
        <xml>
          <x:ExcelWorkbook>
            <x:ExcelWorksheets>
              <x:ExcelWorksheet>
                <x:Name>${(title || 'Export').slice(0, 31)}</x:Name>
                <x:WorksheetOptions>
                  <x:DisplayGridlines/>
                </x:WorksheetOptions>
              </x:ExcelWorksheet>
            </x:ExcelWorksheets>
          </x:ExcelWorkbook>
        </xml>
        <![endif]-->
        <meta http-equiv="content-type" content="application/vnd.ms-excel; charset=UTF-8"/>
      </head>
      <body style="font-family:Arial, sans-serif;font-size:10pt;">
        <table style="margin-bottom:12px;">
          <tr>
            <td colspan="${headers.length}" style="font-size:8pt;color:#64748b;font-weight:bold;text-transform:uppercase;">
              RÉPUBLIQUE DE CÔTE D'IVOIRE • MINISTÈRE DES FINANCES • CODE CIMA (CRCA)
            </td>
          </tr>
          <tr>
            <td colspan="${headers.length}" style="font-size:14pt;font-weight:bold;color:#0f172a;padding-bottom:3px;">
              LE PHARE COURTAGE & GESTION D'ASSURANCES
            </td>
          </tr>
          <tr>
            <td colspan="${headers.length}" style="font-size:12pt;font-weight:bold;color:#0284c7;padding-bottom:6px;">
              ${title || 'ÉTAT D\'EXPORTATION OFFICIEL'}
            </td>
          </tr>
          ${subtitle ? `<tr><td colspan="${headers.length}" style="font-size:9pt;color:#475569;padding-bottom:8px;">${subtitle}</td></tr>` : ''}
          ${metaRows}
        </table>
        <table border="1" style="border-collapse:collapse;width:100%;">
          <thead>
            <tr>${headerCells}</tr>
          </thead>
          <tbody>
            ${bodyRows}
            ${totalRowHtml}
          </tbody>
        </table>
        <div style="margin-top:16px;font-size:8pt;color:#64748b;font-style:italic;">
          Document certifié conforme généré automatiquement le ${new Date().toLocaleDateString('fr-FR')} à ${new Date().toLocaleTimeString('fr-FR')}.
        </div>
      </body>
    </html>
  `;

  const cleanName = filename.endsWith('.xls') || filename.endsWith('.xlsx') ? filename : `${filename}.xls`;
  const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
  downloadBlob(blob, cleanName);
};

/**
 * Export PDF Officiel Certifié CIMA avec déclenchement direct d'impression PDF et téléchargement
 */
export const exportToPdf = ({ filename, title, subtitle, metadata = {}, headers, rows, totals }) => {
  const metaHtml = Object.entries(metadata)
    .map(([k, v]) => `<div><span style="color:#64748b;font-weight:600;">${k} :</span> <strong>${v}</strong></div>`)
    .join('');

  const headerTh = headers
    .map((h, idx) => `<th style="text-align:${idx > 0 ? 'right' : 'left'};padding:8px 10px;background:#f1f5f9;border-bottom:2px solid #0f172a;font-size:8.5pt;text-transform:uppercase;color:#334155;">${h}</th>`)
    .join('');

  const rowsTr = rows
    .map((row, idx) => {
      const cells = row
        .map((cell, colIdx) => {
          const isNum = typeof cell === 'number' || (typeof cell === 'string' && /^[0-9\s]+(\s*F(CFA)?)?$/.test(cell.trim()));
          const align = colIdx > 0 && isNum ? 'right' : 'left';
          const isBold = colIdx === row.length - 1;
          const color = isBold ? '#0f172a' : '#334155';
          return `<td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;text-align:${align};font-size:9.5pt;font-weight:${isBold ? '700' : '400'};color:${color};">${cell ?? ''}</td>`;
        })
        .join('');
      return `<tr>${cells}</tr>`;
    })
    .join('');

  const totalTr = totals && totals.length > 0
    ? `<tr style="background:#f8fafc;font-weight:800;border-top:2px solid #0f172a;border-bottom:2px solid #0f172a;">
        ${totals.map((t, idx) => `<td style="padding:10px;text-align:${idx > 0 ? 'right' : 'left'};font-size:10pt;color:#0f172a;">${t ?? ''}</td>`).join('')}
       </tr>`
    : '';

  const docHtml = `
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>${title || 'Export Officiel CIMA'}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 12mm 15mm;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff;
      margin: 0;
      padding: 10px;
      font-size: 10pt;
      line-height: 1.4;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .header-box {
      border-bottom: 2px solid #0f172a;
      padding-bottom: 10px;
      margin-bottom: 14px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
    .republic-tag {
      font-size: 7.5pt;
      font-weight: 800;
      letter-spacing: 1px;
      text-transform: uppercase;
      color: #475569;
    }
    .company-title {
      font-size: 14pt;
      font-weight: 900;
      color: #0f172a;
      margin-top: 3px;
    }
    .doc-badge {
      text-align: right;
      font-size: 8pt;
      color: #64748b;
    }
    .doc-badge-status {
      font-weight: 800;
      color: #0284c7;
      margin-top: 2px;
      letter-spacing: 0.5px;
    }
    .meta-box {
      display: flex;
      flex-wrap: wrap;
      gap: 15px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      padding: 10px 14px;
      border-radius: 6px;
      margin-bottom: 16px;
      font-size: 8.5pt;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 16px;
    }
    .legal-notice {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      padding: 10px 12px;
      border-radius: 6px;
      font-size: 8pt;
      color: #166534;
      margin-bottom: 20px;
    }
    .signatures {
      display: flex;
      justify-content: space-between;
      margin-top: 24px;
      padding-top: 14px;
      border-top: 1px dashed #cbd5e1;
      font-size: 8.5pt;
    }
    .sig-col {
      width: 45%;
    }
    .sig-space {
      height: 48px;
      display: flex;
      align-items: flex-end;
      color: #94a3b8;
      font-style: italic;
    }
    @media print {
      .no-print { display: none !important; }
      body { padding: 0; }
    }
  </style>
</head>
<body>
  <div class="header-box">
    <div>
      <div class="republic-tag">RÉPUBLIQUE DE CÔTE D'IVOIRE • MINISTÈRE DES FINANCES • CODE CIMA (CRCA)</div>
      <div class="company-title">LE PHARE COURTAGE & GESTION D'ASSURANCES</div>
      <div style="font-size: 11.5pt; font-weight: 800; color: #0284c7; margin-top: 3px;">${title}</div>
      ${subtitle ? `<div style="font-size: 8.5pt; color: #475569; margin-top: 2px;">${subtitle}</div>` : ''}
    </div>
    <div class="doc-badge">
      <div>Édité le ${new Date().toLocaleDateString('fr-FR')}</div>
      <div class="doc-badge-status">DOCUMENT OFFICIEL CERTIFIÉ</div>
    </div>
  </div>

  <div class="meta-box">
    ${metaHtml}
  </div>

  <table>
    <thead>
      <tr>${headerTh}</tr>
    </thead>
    <tbody>
      ${rowsTr}
      ${totalTr}
    </tbody>
  </table>

  <div class="legal-notice">
    <strong>Attestation de Contrôle & Conformité Fiscale :</strong> Le présent bordereau récapitulatif consolide l'ensemble des émissions de polices, quittances et taxes réglementaires conformément aux dispositions des Articles 13 et suivants du Code CIMA.
  </div>

  <div class="signatures">
    <div class="sig-col">
      <div style="font-weight: 700; color: #334155;">Le Chef de Service Comptabilité & Reporting :</div>
      <div class="sig-space">Visa & Paraphe</div>
    </div>
    <div class="sig-col" style="text-align: right;">
      <div style="font-weight: 700; color: #334155;">Pour la Direction Générale / Visa CIMA :</div>
      <div class="sig-space" style="justify-content: flex-end; color: #0284c7; font-weight: 700;">[ Cachet Officiel ]</div>
    </div>
  </div>

  <script>
    window.onload = function() {
      setTimeout(function() {
        window.print();
      }, 350);
    };
  </script>
</body>
</html>
  `;

  // 1. Open instant Print-to-PDF Window
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(docHtml);
    printWindow.document.close();
  }

  // 2. Also trigger a direct download of the official certified HTML file as fallback
  const cleanName = filename.endsWith('.pdf') ? filename.replace(/\.pdf$/, '.html') : (filename.endsWith('.html') ? filename : `${filename}.html`);
  const blob = new Blob([docHtml], { type: 'text/html;charset=utf-8;' });
  downloadBlob(blob, cleanName);
};

const BORDEREAU_COLUMNS = [
  'Numéro Police', 'Numéro quittance', 'Numéro Avenant', 'Date Emission',
  'Date Effet', 'Date Expiration', 'Prime Nette', 'Accessoire', 'Taxe',
  'Prime TTC', 'Comm. Interm.',
];

const fmtMoney = (v) => Math.round(Number(v || 0)).toLocaleString('fr-FR');
const fmtDate = (v) => {
  if (!v) return '';
  const d = new Date(v);
  return isNaN(d.getTime()) ? String(v) : d.toLocaleDateString('fr-FR');
};

/**
 * Construit le corps HTML du tableau groupé Compagnie > Client > Branche
 * (structure identique au bordereau réglementaire de référence OREOLE ASSURANCE).
 */
const buildBordereauGroupsHtml = (groups) => {
  const th = (label, idx) =>
    `<th style="text-align:${idx > 5 ? 'right' : 'left'};padding:6px 8px;background:#1e293b;color:#fff;border:1px solid #334155;font-size:7.5pt;text-transform:uppercase;">${label}</th>`;

  let html = `<thead><tr>${BORDEREAU_COLUMNS.map(th).join('')}</tr></thead><tbody>`;
  const nbCols = BORDEREAU_COLUMNS.length;

  const groupRow = (label, bg, color = '#0f172a', bold = true) =>
    `<tr><td colspan="${nbCols}" style="padding:5px 8px;background:${bg};color:${color};font-weight:${bold ? 700 : 600};font-size:8.5pt;border:1px solid #cbd5e1;">${label}</td></tr>`;

  const totalRow = (label, totals, bg = '#dbeafe') => `
    <tr style="background:${bg};font-weight:700;">
      <td colspan="6" style="padding:5px 8px;border:1px solid #cbd5e1;font-size:8pt;">${label}</td>
      <td style="padding:5px 8px;border:1px solid #cbd5e1;text-align:right;font-size:8pt;">${fmtMoney(totals.primeNette)}</td>
      <td style="padding:5px 8px;border:1px solid #cbd5e1;text-align:right;font-size:8pt;">${fmtMoney(totals.accessoire)}</td>
      <td style="padding:5px 8px;border:1px solid #cbd5e1;text-align:right;font-size:8pt;">${fmtMoney(totals.taxe)}</td>
      <td style="padding:5px 8px;border:1px solid #cbd5e1;text-align:right;font-size:8pt;">${fmtMoney(totals.primeTtc)}</td>
      <td style="padding:5px 8px;border:1px solid #cbd5e1;text-align:right;font-size:8pt;">${fmtMoney(totals.commission)}</td>
    </tr>`;

  groups.compagnies.forEach((compagnie) => {
    html += groupRow(compagnie.label, '#0f172a', '#ffffff');
    compagnie.clients.forEach((client) => {
      html += groupRow(client.label, '#e2e8f0');
      client.branches.forEach((branche) => {
        html += groupRow(branche.label, '#f1f5f9', '#334155', false);
        branche.lines.forEach((l) => {
          html += `<tr>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;font-size:7.8pt;">${l.numero_police || ''}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;font-size:7.8pt;">${l.numero_quittance || ''}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;font-size:7.8pt;">${l.numero_avenant || ''}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;font-size:7.8pt;">${fmtDate(l.date_emission)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;font-size:7.8pt;">${fmtDate(l.date_effet)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;font-size:7.8pt;">${fmtDate(l.date_expiration)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;text-align:right;font-size:7.8pt;">${fmtMoney(l.prime_nette)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;text-align:right;font-size:7.8pt;">${fmtMoney(l.accessoire)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;text-align:right;font-size:7.8pt;">${fmtMoney(l.taxe)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;text-align:right;font-size:7.8pt;">${fmtMoney(l.prime_ttc)}</td>
            <td style="padding:4px 8px;border:1px solid #e2e8f0;text-align:right;font-size:7.8pt;">${fmtMoney(l.commission_intermediaire)}</td>
          </tr>`;
        });
        html += totalRow(`TOTAL ${branche.label}`, branche.total, '#eff6ff');
      });
      html += totalRow(`TOTAL ${client.label}`, client.total, '#dbeafe');
    });
    html += totalRow(`TOTAL ${compagnie.label}`, compagnie.total, '#bfdbfe');
  });

  html += `<tr style="background:#0f172a;color:#fff;font-weight:800;">
      <td colspan="6" style="padding:8px;border:1px solid #0f172a;font-size:9pt;">TOTAL GÉNÉRAL</td>
      <td style="padding:8px;border:1px solid #0f172a;text-align:right;font-size:9pt;">${fmtMoney(groups.grandTotal.primeNette)}</td>
      <td style="padding:8px;border:1px solid #0f172a;text-align:right;font-size:9pt;">${fmtMoney(groups.grandTotal.accessoire)}</td>
      <td style="padding:8px;border:1px solid #0f172a;text-align:right;font-size:9pt;">${fmtMoney(groups.grandTotal.taxe)}</td>
      <td style="padding:8px;border:1px solid #0f172a;text-align:right;font-size:9pt;">${fmtMoney(groups.grandTotal.primeTtc)}</td>
      <td style="padding:8px;border:1px solid #0f172a;text-align:right;font-size:9pt;">${fmtMoney(groups.grandTotal.commission)}</td>
    </tr>`;

  html += '</tbody>';
  return html;
};

/**
 * Export PDF du bordereau des émissions groupé par Compagnie / Client / Branche
 * (mise en page A4 paysage, identique au modèle réglementaire de référence).
 */
export const exportBordereauPdf = ({ filename, title, subtitle, metadata = {}, groups }) => {
  const metaHtml = Object.entries(metadata)
    .map(([k, v]) => `<div><span style="color:#64748b;font-weight:600;">${k} :</span> <strong>${v}</strong></div>`)
    .join('');

  const docHtml = `
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>${title || 'Bordereau des Émissions'}</title>
  <style>
    @page { size: A4 landscape; margin: 10mm 12mm; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a; background: #ffffff; margin: 0; padding: 8px; font-size: 9pt; line-height: 1.35;
      -webkit-print-color-adjust: exact; print-color-adjust: exact;
    }
    .header-box { border-bottom: 2px solid #0f172a; padding-bottom: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: flex-start; }
    .republic-tag { font-size: 7pt; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; color: #475569; }
    .company-title { font-size: 12pt; font-weight: 900; color: #0f172a; margin-top: 2px; }
    .doc-badge { text-align: right; font-size: 7.5pt; color: #64748b; }
    .doc-badge-status { font-weight: 800; color: #0284c7; margin-top: 2px; letter-spacing: 0.5px; }
    .meta-box { display: flex; flex-wrap: wrap; gap: 12px; background: #f8fafc; border: 1px solid #cbd5e1; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; font-size: 7.8pt; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
    .legal-notice { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 8px 10px; border-radius: 6px; font-size: 7.5pt; color: #166534; margin-top: 10px; }
    @media print { .no-print { display: none !important; } body { padding: 0; } }
  </style>
</head>
<body>
  <div class="header-box">
    <div>
      <div class="republic-tag">RÉPUBLIQUE DE CÔTE D'IVOIRE • MINISTÈRE DES FINANCES • CODE CIMA (CRCA)</div>
      <div class="company-title">LE PHARE COURTAGE & GESTION D'ASSURANCES</div>
      <div style="font-size: 10pt; font-weight: 800; color: #0284c7; margin-top: 2px;">${title}</div>
      ${subtitle ? `<div style="font-size: 7.8pt; color: #475569; margin-top: 2px;">${subtitle}</div>` : ''}
    </div>
    <div class="doc-badge">
      <div>Édité le ${new Date().toLocaleDateString('fr-FR')}</div>
      <div class="doc-badge-status">DOCUMENT OFFICIEL CERTIFIÉ</div>
    </div>
  </div>

  <div class="meta-box">${metaHtml}</div>

  <table>${buildBordereauGroupsHtml(groups)}</table>

  <div class="legal-notice">
    <strong>Attestation de Contrôle & Conformité Fiscale :</strong> Le présent bordereau consolide, par compagnie, par client et par branche, l'ensemble des émissions de polices et quittances de la période conformément aux dispositions des Articles 13 et suivants du Code CIMA.
  </div>

  <script>
    window.onload = function() { setTimeout(function() { window.print(); }, 350); };
  </script>
</body>
</html>
  `;

  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(docHtml);
    printWindow.document.close();
  }

  const cleanName = filename.endsWith('.pdf') ? filename.replace(/\.pdf$/, '.html') : (filename.endsWith('.html') ? filename : `${filename}.html`);
  const blob = new Blob([docHtml], { type: 'text/html;charset=utf-8;' });
  downloadBlob(blob, cleanName);
};

/**
 * Export Excel du bordereau des émissions groupé par Compagnie / Client / Branche.
 */
export const exportBordereauExcel = ({ filename, title, subtitle, metadata = {}, groups }) => {
  const metaRows = Object.entries(metadata)
    .map(([k, v]) => `<tr><td style="font-weight:bold;color:#475569;padding:3px;">${k} :</td><td colspan="${BORDEREAU_COLUMNS.length - 1}" style="padding:3px;">${v}</td></tr>`)
    .join('');

  const html = `
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
      <head>
        <!--[if gte mso 9]>
        <xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>
          <x:Name>${(title || 'Bordereau').slice(0, 31)}</x:Name>
          <x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>
        </x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml>
        <![endif]-->
        <meta http-equiv="content-type" content="application/vnd.ms-excel; charset=UTF-8"/>
      </head>
      <body style="font-family:Arial, sans-serif;font-size:10pt;">
        <table style="margin-bottom:12px;">
          <tr><td colspan="${BORDEREAU_COLUMNS.length}" style="font-size:14pt;font-weight:bold;color:#0f172a;">LE PHARE COURTAGE & GESTION D'ASSURANCES</td></tr>
          <tr><td colspan="${BORDEREAU_COLUMNS.length}" style="font-size:12pt;font-weight:bold;color:#0284c7;padding-bottom:6px;">${title || ''}</td></tr>
          ${subtitle ? `<tr><td colspan="${BORDEREAU_COLUMNS.length}" style="font-size:9pt;color:#475569;padding-bottom:8px;">${subtitle}</td></tr>` : ''}
          ${metaRows}
        </table>
        <table border="1" style="border-collapse:collapse;width:100%;">
          ${buildBordereauGroupsHtml(groups)}
        </table>
      </body>
    </html>
  `;

  const cleanName = filename.endsWith('.xls') || filename.endsWith('.xlsx') ? filename : `${filename}.xls`;
  const blob = new Blob([html], { type: 'application/vnd.ms-excel;charset=utf-8;' });
  downloadBlob(blob, cleanName);
};

/**
 * Export XML Réglementaire CRCA
 */
export const exportToXml = ({ filename, rootTag = 'BORDEREAU_CIMA', metadata = {}, items = [] }) => {
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += `<${rootTag}>\n`;
  xml += '  <ENTETE_OFFICIEL>\n';
  xml += `    <ORGANISME>LE PHARE COURTAGE &amp; GESTION D'ASSURANCES</ORGANISME>\n`;
  xml += `    <PAYS>COTE D IVOIRE</PAYS>\n`;
  xml += `    <CODE_REGULATEUR>CRCA_CIMA</CODE_REGULATEUR>\n`;
  xml += `    <DATE_EDITION>${new Date().toISOString()}</DATE_EDITION>\n`;
  Object.entries(metadata).forEach(([k, v]) => {
    const cleanKey = k.toUpperCase().replace(/[^A-Z0-9_]/g, '_');
    xml += `    <${cleanKey}>${String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</${cleanKey}>\n`;
  });
  xml += '  </ENTETE_OFFICIEL>\n';
  xml += '  <LIGNES_PRODUCTION>\n';
  items.forEach((item, idx) => {
    xml += `    <LIGNE id="${idx + 1}">\n`;
    Object.entries(item).forEach(([k, v]) => {
      const cleanKey = k.toUpperCase().replace(/[^A-Z0-9_]/g, '_');
      xml += `      <${cleanKey}>${String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</${cleanKey}>\n`;
    });
    xml += '    </LIGNE>\n';
  });
  xml += '  </LIGNES_PRODUCTION>\n';
  xml += `</${rootTag}>\n`;

  const cleanName = filename.endsWith('.xml') ? filename : `${filename}.xml`;
  const blob = new Blob([xml], { type: 'application/xml;charset=utf-8;' });
  downloadBlob(blob, cleanName);
};
