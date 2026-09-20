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

/* =========================================================================
   IMPRESSION DES DEVIS/FACTURES PROFORMA — 3 GABARITS REPRIS D'URANUS
   (Auto, IA/Voyage/Transport, MRH), d'après les modèles PDF fournis par
   OREOLE ASSURANCE. Ouvre une fenêtre d'impression dédiée, indépendante
   du contenu affiché à l'écran.
   ========================================================================= */

const money = (v) => Number(v || 0).toLocaleString('fr-FR');

const formatFrDate = (value) => {
  if (!value) return '—';
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
};

// Conversion d'un nombre entier (FCFA, pas de décimales) en toutes lettres françaises,
// pour la mention "En votre aimable règlement ... la somme de [montant en toutes lettres]"
// du gabarit Auto (cf. FACTURE AUTO PREFORMA.pdf : "TRENTE MILLE CINQ CENT DIX").
export const numberToFrenchWords = (num) => {
  const n = Math.round(Math.abs(Number(num) || 0));
  if (n === 0) return 'ZERO';

  const unites = ['', 'UN', 'DEUX', 'TROIS', 'QUATRE', 'CINQ', 'SIX', 'SEPT', 'HUIT', 'NEUF', 'DIX',
    'ONZE', 'DOUZE', 'TREIZE', 'QUATORZE', 'QUINZE', 'SEIZE', 'DIX-SEPT', 'DIX-HUIT', 'DIX-NEUF'];
  const dizaines = ['', '', 'VINGT', 'TRENTE', 'QUARANTE', 'CINQUANTE', 'SOIXANTE', 'SOIXANTE', 'QUATRE-VINGT', 'QUATRE-VINGT'];

  // isFinalGroup: "CENT" ne prend un "S" que si le groupe de 3 chiffres est
  // le dernier mot de l'écriture (ex. "DEUX CENTS" seul), jamais lorsqu'il
  // est suivi de MILLE/MILLION/MILLIARD (ex. "DEUX CENT MILLE", sans S).
  const troisChiffres = (num3, isFinalGroup) => {
    let out = '';
    const c = Math.floor(num3 / 100);
    const reste = num3 % 100;
    if (c > 0) {
      out += c > 1 ? `${unites[c]} CENT` : 'CENT';
      if (reste === 0 && c > 1 && isFinalGroup) out += 'S';
    }
    if (reste > 0) {
      if (out) out += ' ';
      if (reste < 20) {
        out += unites[reste];
      } else {
        const d = Math.floor(reste / 10);
        const u = reste % 10;
        if (d === 8) {
          // Quatre-vingts (seul) prend un S, quatre-vingt-un/-deux... n'en prend pas.
          out += u > 0 ? `${dizaines[d]}-${unites[u]}` : `${dizaines[d]}S`;
        } else if (d === 7 || d === 9) {
          // Soixante et onze (71) est la seule exception avec "ET" dans cette tranche.
          out += d === 7 && u === 1 ? `${dizaines[d]} ET ${unites[10 + u]}` : `${dizaines[d]}-${unites[10 + u]}`;
        } else if (u === 1 && d >= 2 && d <= 6) {
          // Vingt et un, trente et un, ..., soixante et un.
          out += `${dizaines[d]} ET UN`;
        } else {
          out += dizaines[d] + (u > 0 ? `-${unites[u]}` : '');
        }
      }
    }
    return out;
  };

  const tranches = [
    { valeur: 1000000000, libelle: 'MILLIARD' },
    { valeur: 1000000, libelle: 'MILLION' },
    { valeur: 1000, libelle: 'MILLE' },
  ];

  let reste = n;
  const parties = [];
  for (const t of tranches) {
    const q = Math.floor(reste / t.valeur);
    if (q > 0) {
      const mot = t.libelle === 'MILLE' && q === 1 ? 'MILLE' : `${troisChiffres(q, false)} ${t.libelle}${q > 1 && t.libelle !== 'MILLE' ? 'S' : ''}`;
      parties.push(mot);
      reste %= t.valeur;
    }
  }
  if (reste > 0) parties.push(troisChiffres(reste, true));

  return parties.join(' ').replace(/\s+/g, ' ').trim();
};

const getCompagnieLogoUrl = (compagnieName) => {
  const c = String(compagnieName || '').toLowerCase();
  if (c.includes('nsia')) return '/assets/print/logo-nsia.jpg';
  if (c.includes('sunu')) return '/assets/print/logo-sunu.png';
  return null;
};

const printDocHeader = (quote, docTitle) => {
  const logo = getCompagnieLogoUrl(quote.compagnie);
  return `
    <div class="facture-header">
      <img src="/assets/print/logo-oreole-entete.png" alt="OREOLE Assurances" class="header-logo-oreole" />
      ${logo
        ? `<img src="${logo}" alt="${quote.compagnie}" class="header-logo-compagnie" />`
        : `<div class="header-compagnie-text">${quote.compagnie || ''}</div>`}
    </div>
    <div class="facture-title">${docTitle}</div>
  `;
};

const printDocFooter = (withBarcode) => `
  <div class="facture-footer">
    ${withBarcode ? `
      <div class="barcode-block">
        <img src="/assets/print/codebar.png" alt="Code-barres document" />
        <div class="barcode-ref">Réf. document</div>
      </div>
    ` : '<div></div>'}
    <img src="/assets/print/logo-oreole-pied.png" alt="OREOLE Assurances" class="footer-logo-oreole" />
  </div>
`;

// --- GABARIT A : AUTO (facture proforma / facture de prime définitive) ---
const buildAutoFacture = (quote) => {
  const isPolice = Boolean(quote.confirme);
  const numero = quote.numero_police_compagnie || quote.numerodevis;
  const docTitle = isPolice
    ? `FACTURE DE PRIME N°${numero}`
    : `FACTURE PROFORMA DE LA PRIME N°${numero}`;
  const idLabel = isPolice ? 'Id. Police' : 'Id. Devis';
  const numLabel = isPolice ? 'N° Police' : 'N° Devis';
  const telephone = quote.details?.telephoneClient || quote.raw?.numerotelephoneassure || '—';
  const numeroActe = quote.raw?.numeroavenant || quote.details?.numeroAvenant || '0000001';

  return `
    ${printDocHeader(quote, docTitle)}
    <div class="sous-titre">ASSURANCE ${(quote.produit || 'AUTOMOBILE').toUpperCase()}</div>

    <table class="cadre-unique">
      <tr><td colspan="6" class="ligne-compagnie">Compagnie <strong>${(quote.compagnie || '').toUpperCase()}</strong></td></tr>
      <tr>
        <td colspan="3" class="entete-bloc" style="text-align:center;">SOUSCRIPTEUR</td>
        <td colspan="3" class="entete-bloc" style="text-align:center;">ASSURE</td>
      </tr>
      <tr>
        <td colspan="3" style="text-align:center;">
          <strong>${(quote.souscripteur || quote.client_nom || '').toUpperCase()}</strong><br/>-<br/><strong>${telephone}</strong>
        </td>
        <td colspan="3" style="text-align:center;">
          <strong>${(quote.nomassure || quote.client_nom || '').toUpperCase()}</strong><br/>-<br/><strong>${telephone}</strong>
        </td>
      </tr>
      <tr class="ligne-labels">
        <td>${idLabel}</td><td>${numLabel}</td><td>Effet</td><td>N° Acte</td><td>Effect Acte</td><td>Expiration</td>
      </tr>
      <tr class="ligne-valeurs">
        <td><strong>${quote.iddevis}</strong></td>
        <td><strong>${numero}</strong></td>
        <td><strong>${formatFrDate(quote.date_effet)}</strong></td>
        <td><strong>${numeroActe}</strong></td>
        <td><strong>${formatFrDate(quote.date_effet)}</strong></td>
        <td><strong>${formatFrDate(quote.date_expiration)}</strong></td>
      </tr>
      <tr><td colspan="6" style="border:none;height:10px;"></td></tr>
      <tr class="ligne-labels">
        <td>PRIME NETTE</td><td>ACCESSOIRE</td><td>TAXES</td><td>FDG</td><td>CEDEAO</td><td>PRIME TTC</td>
      </tr>
      <tr class="ligne-valeurs">
        <td><strong>${money(quote.prime_nette)}</strong></td>
        <td><strong>${money(quote.accessoires)}</strong></td>
        <td><strong>${money(quote.taxes)}</strong></td>
        <td><strong>${money(quote.fga)}</strong></td>
        <td><strong>${money(quote.cedeao)}</strong></td>
        <td><strong>${money(quote.prime_totale)}</strong></td>
      </tr>
    </table>

    <p class="texte-politesse">
      En votre aimable règlement par chèque à l'ordre de ${(quote.compagnie || '').toUpperCase()} ou par tout règlement la somme de
      ${numberToFrenchWords(quote.prime_totale)} FRANCS CFA.
    </p>
    <p class="texte-politesse">Pièces jointes : 3 exemplaires de l'avenant en référence dont 2 à nous retourner après signature.</p>
    <p class="texte-politesse">Dans cette attente, nous vous prions d'agréer l'expression de nos sentiments dévoués.</p>

    <div class="bloc-signature-droite">
      <div>Fait à Abidjan, le <strong>${formatFrDate(new Date())}</strong>.</div>
      <div style="margin-top:28px;"><strong>Pour la société</strong></div>
    </div>

    ${printDocFooter(true)}
  `;
};

// --- CONDITIONS PARTICULIÈRES (échéancier de police, distinct de la facture
// proforma) — d'après CONDITIONS PARTICULIERES ASSURANCE AUTO.pdf (police
// NSIA n°1186201263156M). Détail véhicule + tableau des garanties ligne par
// ligne avec plafond/franchise/prime/réductions BNS-CCIAL.
const buildConditionsParticulieresAuto = (quote) => {
  const numero = quote.numero_police_compagnie || quote.numerodevis;
  const d = quote.details || {};
  const raw = quote.raw || {};
  const garanties = raw.garanties || d.garanties || [];
  const bnsDefaut = quote.bonus_malus || d.bonusMalus || 0;
  const dash = (v) => (v === undefined || v === null || v === '' ? '—' : v);
  const num = (v) => (v === undefined || v === null || v === '' ? 0 : Number(v) || 0);
  const dureeJours = raw.duree_terme_jours
    ?? (quote.date_effet && quote.date_expiration
      ? Math.round((new Date(quote.date_expiration) - new Date(quote.date_effet)) / 86400000) + 1
      : '—');

  // Mouvement / avenant (Affaire nouvelle, Renouvellement, ...) : le titre
  // devient « Avenant de RENOUVELLEMENT » comme sur l'exemplaire courtier.
  const mouvement = String(raw.libelle_avenant || d.libelleAvenant || d.mouvement || quote.libelle_avenant || 'AFFAIRE NOUVELLE').toUpperCase();
  const numeroAvenant = raw.numeroavenant || d.numeroAvenant || quote.numeroavenant || 0;
  const titreAvenant = /^AFFAIRE\s+NOUVELLE/.test(mouvement) ? '' : `Avenant de ${mouvement.replace(/^AVENANT\s+(DE\s+)?/, '')}`;
  const offre = d.offreSelectionnee || raw.libelle_offre || quote.libelle_offre || quote.produit || '';
  const adresse = d.adresseClient || raw.adresse || raw.adressegeoclient || '—';
  const nomAssure = (quote.nomassure || quote.client_nom || '').toUpperCase();
  const conducteur = (d.conducteurHabituel || raw.conducteur_habituel || nomAssure || '').toUpperCase();

  const franchiseTxt = (g) => {
    if (g.libelle_franchise) return g.libelle_franchise;
    const taux = g.taux_franchise ?? g.tauxfranchise;
    const min = g.min_franchise ?? g.minfranchise;
    const fixe = g.montant_franchise || g.franchise;
    if (taux && Number(taux) > 0) return `${taux}% minimum ${min ? money(min) : 0}`;
    if (fixe && Number(fixe) > 0) return money(fixe);
    return 'NEANT';
  };

  const lignes = garanties.map((g) => {
    const primeAnnuelle = num(g.prime_annuelle);
    const primeNette = num(g.prime_nette);
    const comptant = num(g.prime_comptant ?? g.prime_nette_comptant ?? g.prime_nette);
    return {
      libelle: g.libelle || g.nom_garantie || g.id_garantie || '—',
      acquise: (g.acquise ?? g.souscrite) ? 'OUI' : 'NON',
      capital: g.capital && Number(g.capital) > 0 ? money(g.capital) : '',
      franchise: franchiseTxt(g),
      primeAnnuelle: g.prime_annuelle === undefined || g.prime_annuelle === null ? '' : money(primeAnnuelle),
      bns: `${g.taux_reduction_bns ?? bnsDefaut ?? 0}%`,
      autres: `${g.taux_reduction_commerciale ?? d.reductionCommerciale ?? 0} %`,
      nette: money(primeNette),
      comptant: money(comptant),
      primeAnnuelleNum: primeAnnuelle,
      netteNum: primeNette,
      comptantNum: comptant,
    };
  });
  const totalAnnuelle = lignes.reduce((t, l) => t + l.primeAnnuelleNum, 0);
  const totalNette = lignes.reduce((t, l) => t + l.netteNum, 0);
  const totalComptant = lignes.reduce((t, l) => t + l.comptantNum, 0);

  const garantieRow = (l) => `
    <tr>
      <td class="g-lib">${l.libelle}</td>
      <td>${l.acquise}</td>
      <td class="g-num">${l.capital}</td>
      <td class="g-lib">${l.franchise}</td>
      <td class="g-num">${l.primeAnnuelle}</td>
      <td>${l.bns}</td>
      <td>${l.autres}</td>
      <td class="g-num">${l.nette}</td>
      <td class="g-num">${l.comptant}</td>
    </tr>`;

  const sr = raw.securite_routiere || d.securiteRoutiere || {};
  const srLine = sr.deces || sr.ipt || sr.ft
    ? `Décès : ${money(sr.deces)} / IPT : ${money(sr.ipt)} / FT : ${money(sr.ft)}`
    : (garanties.some((g) => /s[ée]curit[ée] routi[èe]re/i.test(g.libelle || g.nom_garantie || ''))
      ? 'Garantie souscrite (capitaux selon la formule choisie)'
      : 'Non souscrite');

  return `
    <div class="cp-entete">
      <div class="cp-entete-logos">
        ${printDocHeader(quote, titreAvenant)}
      </div>
      <div class="cp-tampon">EXEMPLAIRE<br/>COURTIER</div>
    </div>

    <div class="cp-deux-blocs">
      <table class="cadre-unique cp-bloc-client">
        <tr><td class="label">Numéro</td><td>${dash(quote.client_id)}</td></tr>
        <tr><td class="label">Nom</td><td><strong>${(quote.souscripteur || quote.client_nom || '').toUpperCase()}</strong></td></tr>
        <tr><td class="label">Adresse</td><td>${adresse}</td></tr>
        <tr><td class="label">Téléphone</td><td>${dash(d.telephoneClient || raw.telephoneclient || raw.numerotelephoneassure)}</td></tr>
        <tr><td class="label">Profession</td><td>${dash(d.profession || raw.profession)}</td></tr>
        <tr><td class="label">Réseau</td><td>${dash(d.reseau || raw.libelle_intermediaire || 'OREOLE')}</td></tr>
      </table>
      <table class="cadre-unique cp-bloc-police">
        <tr><td class="label">Quittance</td><td>${dash(raw.numero_quittance || d.numeroQuittance)}</td></tr>
        <tr><td class="label">N° Police</td><td><strong>${dash(numero)}</strong> &nbsp; Avenant <strong>${numeroAvenant}</strong></td></tr>
        <tr><td class="label">Assuré(e)</td><td>${nomAssure}</td></tr>
        <tr><td class="label">Adresse</td><td>${adresse}</td></tr>
        <tr><td class="label">Mouvement</td><td>${mouvement}</td></tr>
        <tr><td class="label">Offre</td><td>${String(offre).toUpperCase()}</td></tr>
        <tr><td class="label">Effet</td><td>${formatFrDate(quote.date_effet)} &nbsp; Expiration : ${formatFrDate(quote.date_expiration)} &nbsp; Durée : <strong>${dureeJours}</strong></td></tr>
        <tr><td class="label">Émission</td><td>${formatFrDate(quote.date_emission)} &nbsp; Compagnie : <strong>${(quote.compagnie || '').toUpperCase()}</strong></td></tr>
      </table>
    </div>

    <div class="titre-cp">
      <div>CONDITIONS PARTICULIÈRES</div>
      <div>ASSURANCE ${(quote.produit || 'AUTOMOBILE').toUpperCase()}</div>
    </div>

    <table class="cadre-unique cp-info">
      <tr>
        <td class="label">N° Immatriculation</td><td>${dash(d.immatriculation)}</td>
        <td class="label">1ère mise en circulation</td><td>${d.dateMec ? formatFrDate(d.dateMec) : '—'}</td>
        <td class="label">Énergie</td><td>${dash(d.energie)}</td>
      </tr>
      <tr>
        <td class="label">Marque</td><td>${dash(d.marqueVehicule)}</td>
        <td class="label">Genre</td><td>${dash(d.genreVehicule)}</td>
        <td class="label">Carrosserie</td><td>${dash(d.carrosserie)}</td>
      </tr>
      <tr>
        <td class="label">Nbre de Place</td><td>${dash(d.nombrePlace)}</td>
        <td class="label">Puissance</td><td>${dash(d.puissanceFiscale)}</td>
        <td class="label">Puissance Réelle</td><td>${dash(d.puissanceReelle ?? 0)}</td>
      </tr>
      <tr>
        <td class="label">Poids vide</td><td>${dash(d.poidsVide ?? 0)}</td>
        <td class="label">Charge Utile</td><td>${dash(d.chargeUtile ?? 0)}</td>
        <td class="label">PTAC</td><td>${dash(d.ptac ?? 0)}</td>
      </tr>
      <tr>
        <td class="label">Type</td><td>${dash(d.typeVehicule || d.genreVehicule)}</td>
        <td class="label">N° de série / châssis</td><td>${dash(d.numeroChassis)}</td>
        <td class="label">Valeur Neuve</td><td>${d.valeurNeuf ? money(d.valeurNeuf) : '—'}</td>
      </tr>
      <tr>
        <td class="label">Valeur Vénale</td><td>${d.valeurVenale ? money(d.valeurVenale) : '—'}</td>
        <td class="label">Bonus / Malus</td><td>${bnsDefaut}%</td>
        <td class="label">Couleur</td><td>${dash(d.couleur)}</td>
      </tr>
    </table>

    <table class="cadre-unique cp-offre">
      <tr>
        <td class="label">Offre</td><td><strong>${String(offre).toUpperCase()}</strong></td>
        <td class="label">Conducteur habituel</td><td><strong>${conducteur}</strong></td>
      </tr>
    </table>

    <table class="tableau-garanties cp-garanties">
      <tr class="ligne-labels">
        <td>Garanties</td><td>États</td><td>Sommes Garanties</td><td>Franchise</td>
        <td>Prime Annuelle</td><td>BNS</td><td>Autres</td><td>Nette Annuelle</td><td>Prime Comptant</td>
      </tr>
      ${lignes.length > 0
        ? lignes.map(garantieRow).join('')
        : '<tr><td colspan="9" style="text-align:center;color:#64748b;">Aucune garantie enregistrée sur ce devis</td></tr>'}
      <tr class="ligne-total">
        <td class="g-lib" colspan="4">TOTAL VÉHICULE : ${dash(d.immatriculation)}</td>
        <td class="g-num">${money(totalAnnuelle)}</td><td></td><td></td>
        <td class="g-num">${money(totalNette)}</td><td class="g-num">${money(totalComptant)}</td>
      </tr>
    </table>

    <div class="cp-securite"><strong>SÉCURITÉ ROUTIÈRE :</strong> ${srLine}</div>
    <div class="cp-securite"><strong>Individuelle Chauffeur :</strong> ${dash(raw.individuelle_chauffeur || d.individuelleChauffeur || '')}</div>

    <div class="cp-bas">
      <div class="cp-mentions">
        <p>Les présentes Conditions Particulières prévalent sur les Conditions Générales ou Conventions Spéciales pour autant qu'elles leur sont contraires.</p>
        <p class="cp-visa">Visa : MEF/DGTCP/DA N°736 DU 31 DÉCEMBRE 1999</p>
      </div>
      <table class="cadre-unique cp-recap">
        <tr><td class="label">Prime Nette</td><td>${money(quote.prime_nette)}</td></tr>
        <tr><td class="label">Accessoire</td><td>${money(quote.accessoires)}</td></tr>
        <tr><td class="label">Taxe d'enregistrement</td><td>${money(quote.taxes)}</td></tr>
        <tr><td class="label">FGA</td><td>${money(quote.fga)}</td></tr>
        <tr><td class="label">Prime TTC</td><td>${money(quote.prime_totale)}</td></tr>
        <tr class="ligne-total"><td class="label">Total net à payer</td><td><strong>${money(quote.prime_totale)} FCFA</strong></td></tr>
      </table>
    </div>

    <div class="bloc-signature-droite">
      <div>Fait à Abidjan, le <strong>${formatFrDate(new Date())}</strong>.</div>
    </div>
    <div class="signatures-deux-colonnes" style="margin-top:30px;">
      <div><em>L'assuré</em></div>
      <div><em>Pour la compagnie</em></div>
    </div>

    ${printDocFooter(true)}
  `;
};

// --- GABARIT B : IA / VOYAGE / TRANSPORT / SANTE (facture simple à blocs) ---
const buildSimpleFacture = (quote) => {
  const branche = String(quote.branche || quote.produit || '').toLowerCase();
  const isIa = branche.includes('ia') || branche.includes('accident');
  const isVoyage = branche.includes('voyag');
  const numero = quote.numero_police_compagnie || quote.numerodevis;
  const ayantsDroit = quote.raw?.ayants_droit || quote.details?.ayantsDroit || [];

  return `
    ${printDocHeader(quote, `FACTURE N° ${numero}`)}

    <div class="bloc-titre">SOUSCRIPTEUR</div>
    <table class="bloc-cadre">
      <tr><td class="label">Nom</td><td>${(quote.souscripteur || quote.client_nom || '').toUpperCase()}</td></tr>
      <tr><td class="label">Adresse</td><td>${quote.raw?.adresse || '—'}</td></tr>
    </table>

    ${isIa ? `
      <div class="bloc-titre">ASSURES, AYANTS DROIT</div>
      <table class="bloc-cadre bloc-tableau">
        <tr class="ligne-labels"><td>Nom et prénoms</td><td>Qualité</td><td>Part</td></tr>
        ${ayantsDroit.length > 0
          ? ayantsDroit.map((a) => `<tr><td>${a.nom || a.nom_prenoms || '—'}</td><td>${a.qualite || '—'}</td><td>${a.part ? `${a.part}%` : '—'}</td></tr>`).join('')
          : '<tr><td colspan="3" style="text-align:center;color:#94a3b8;">Aucun ayant droit enregistré</td></tr>'}
      </table>
    ` : `
      <div class="bloc-titre">ASSURE</div>
      <table class="bloc-cadre">
        <tr><td class="label">Nom</td><td>${(quote.nomassure || quote.client_nom || '').toUpperCase()}</td></tr>
        <tr><td class="label">Adresse</td><td>${quote.raw?.adresse_assure || '—'}</td></tr>
      </table>
    `}

    <div class="bloc-titre">Référence police et périodicité</div>
    <table class="bloc-cadre">
      <tr><td class="label">Au titre de la police</td><td>${(quote.produit || '').toUpperCase()}</td></tr>
      <tr><td class="label">Numéro Devis</td><td>${numero}</td></tr>
      ${isVoyage ? `<tr><td class="label">Numéro Attestation</td><td>${quote.raw?.numero_attestation || '—'}</td></tr>` : ''}
      <tr><td class="label">Pour la période allant du</td><td>${formatFrDate(quote.date_effet)} Au ${formatFrDate(quote.date_expiration)}</td></tr>
    </table>

    <div class="bloc-titre">Détail de la facture</div>
    <table class="bloc-cadre">
      <tr><td class="label">Prime Nette</td><td>${money(quote.prime_nette)}</td></tr>
      <tr><td class="label">Accessoire</td><td>${money(quote.accessoires)}</td></tr>
      <tr><td class="label">Taxe d'enregistrement</td><td>${money(quote.taxes)}</td></tr>
      <tr class="ligne-total"><td class="label">PRIME TOTALE A PAYER</td><td><strong>${money(quote.prime_totale)}</strong></td></tr>
    </table>

    <div class="mention-cima">
      Conformément à l'Article 13 du Code des Assurances CIMA, la prime doit être payée intégralement et d'avance.
      À défaut de paiement dans les délais réglementaires (60 jours pour les risques autres que Maladie, Automobile
      et Transport de Marchandises), la garantie peut être suspendue puis le contrat résilié de plein droit.
      Tout chèque impayé entraîne la nullité du paiement et un délai de régularisation de 8 jours.
    </div>

    <div class="bloc-signature-simple">
      <div>Fait à Abidjan, le <strong>${formatFrDate(new Date())}</strong>.</div>
      <div class="signatures-deux-colonnes">
        <div>LE SOUSCRIPTEUR</div>
        <div>LA COMPAGNIE</div>
      </div>
    </div>

    ${printDocFooter(false)}
  `;
};

// --- GABARIT C : MRH (proposition d'assurance habitation) ---
const buildMrhFacture = (quote) => {
  const numero = quote.numero_police_compagnie || quote.numerodevis;
  const garanties = quote.raw?.garanties || quote.details?.garanties || [];
  const dureeJours = quote.raw?.duree_terme_jours
    ?? (quote.date_effet && quote.date_expiration
      ? Math.round((new Date(quote.date_expiration) - new Date(quote.date_effet)) / 86400000)
      : null);

  return `
    ${printDocHeader(quote, '')}
    <div class="titre-mrh">
      <div>Assurance MULTIRISQUES HABITATION</div>
      <div>Proposition ${(quote.compagnie || 'NSIA CI')}</div>
    </div>

    <div class="ligne-identifiants">
      N° CLIENT : ${quote.client_id || '—'} &nbsp;|&nbsp; Id. POLICE : ${quote.iddevis} &nbsp;|&nbsp; N° DEVIS : ${numero}
    </div>

    <table class="bloc-libre">
      <tr>
        <td><strong>SOUSCRIPTEUR:</strong> ${(quote.souscripteur || quote.client_nom || '').toUpperCase()}</td>
        <td><strong>ADRESSE:</strong> ${quote.raw?.adresse || '—'}</td>
      </tr>
      <tr>
        <td><strong>ASSURE:</strong> ${(quote.nomassure || quote.client_nom || '').toUpperCase()}</td>
        <td><strong>DATE NAISSANCE:</strong> ${quote.raw?.date_naissance_assure ? formatFrDate(quote.raw.date_naissance_assure) : '—'}</td>
      </tr>
    </table>

    <div class="ligne-dates">
      Du: ${formatFrDate(quote.date_effet)} &nbsp;&nbsp; au ${formatFrDate(quote.date_expiration)} à minuit &nbsp;&nbsp; Durée: ${dureeJours ?? '—'} Jours
    </div>

    <table class="tableau-garanties">
      <tr class="ligne-labels">
        <td>Garantie</td><td>Capitaux</td><td>Franchise</td><td>Min Franchise</td><td>Max Franchise</td><td>Taux Frch (%)</td><td>Prime Annuelle</td><td>Prime Nette</td>
      </tr>
      ${garanties.length > 0
        ? garanties.map((g) => `
          <tr>
            <td>${g.libelle || g.nom || '—'}</td>
            <td>${g.capital ? money(g.capital) : '—'}</td>
            <td>${g.franchise ? money(g.franchise) : '—'}</td>
            <td>${g.min_franchise ? money(g.min_franchise) : '—'}</td>
            <td>${g.max_franchise ? money(g.max_franchise) : '—'}</td>
            <td>${g.taux_franchise ?? '—'}</td>
            <td>${g.prime_annuelle ? money(g.prime_annuelle) : '—'}</td>
            <td>${g.prime_nette ? money(g.prime_nette) : '—'}</td>
          </tr>`).join('')
        : ['VOL', 'BRIS DE GLACES', 'DOMMAGES ÉLECTRIQUES', 'DÉGÂTS DES EAUX', 'TEMPÊTE OURAGAN CYCLONE', 'INCENDIE', 'RESPONSABILITÉ CIVILE VIE PRIVÉE', 'SÉJOUR VOYAGE']
            .map((lib) => `<tr><td>${lib}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td></tr>`).join('')}
    </table>

    <table class="recap-vertical">
      <tr><td class="label">PRIME NETTE</td><td>: ${money(quote.prime_nette)} FCFA</td></tr>
      <tr><td class="label">TAXES</td><td>: ${money(quote.taxes)} FCFA</td></tr>
      <tr><td class="label">ACCESSOIRE</td><td>: ${money(quote.accessoires)} FCFA</td></tr>
      <tr class="ligne-total"><td class="label">PRIME TTC</td><td>: ${money(quote.prime_totale)} FCFA</td></tr>
      <tr class="ligne-total"><td class="label">NET A PAYER</td><td>: ${money(quote.prime_totale)} FCFA</td></tr>
    </table>

    <div class="mention-courte">
      Cette offre n'est qu'une proposition d'assurance. Elle n'engage en rien la compagnie et a une durée de validité
      d'un (1) mois à compter de sa date d'émission.
    </div>

    ${printDocFooter(false)}
  `;
};

const PRINT_STYLES = `
  @page { size: A4 portrait; margin: 14mm 16mm; }
  body {
    font-family: Arial, Helvetica, sans-serif;
    color: #0f172a;
    font-size: 10pt;
    line-height: 1.45;
    margin: 0;
    padding: 10px;
  }
  .facture-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
  .header-logo-oreole { height: 46px; }
  .header-logo-compagnie { height: 40px; }
  .header-compagnie-text { font-weight: 800; font-size: 12pt; }
  .facture-title { text-align: center; font-weight: 800; font-size: 12pt; text-transform: uppercase; margin-bottom: 4px; }
  .sous-titre { font-weight: 700; margin-bottom: 10px; }
  .titre-mrh { text-align: center; font-size: 13pt; margin-bottom: 10px; }
  table.cadre-unique { width: 100%; border-collapse: collapse; border: 1.5px solid #0f172a; margin-bottom: 14px; }
  table.cadre-unique td { border: 1px solid #64748b; padding: 6px 8px; font-size: 9pt; }
  .ligne-compagnie { font-size: 9.5pt; }
  .entete-bloc { font-weight: 700; background: #f1f5f9; }
  .ligne-labels td { font-weight: 600; text-align: center; background: #f8fafc; font-size: 8.3pt; text-transform: uppercase; }
  .ligne-valeurs td { text-align: center; }
  .texte-politesse { font-size: 8.8pt; margin: 4px 0; }
  .bloc-signature-droite { text-align: right; margin-top: 20px; font-size: 9.5pt; }
  .bloc-titre { font-weight: 700; background: #eef2ff; border: 1px solid #c7d2fe; padding: 4px 8px; margin-top: 12px; font-size: 9pt; }
  table.bloc-cadre { width: 100%; border-collapse: collapse; border: 1px solid #cbd5e1; margin-bottom: 4px; }
  table.bloc-cadre td { border-bottom: 1px solid #e2e8f0; padding: 5px 8px; font-size: 9pt; }
  table.bloc-cadre td.label { font-weight: 600; color: #475569; width: 220px; }
  table.bloc-tableau td { text-align: center; }
  .ligne-total td { font-weight: 800; border-top: 2px solid #0f172a !important; }
  .mention-cima { border: 1px solid #cbd5e1; padding: 8px 10px; font-size: 7.6pt; text-align: justify; color: #334155; margin: 14px 0; background: #f8fafc; }
  .mention-courte { font-size: 8.5pt; font-style: italic; color: #475569; margin-top: 14px; }
  .bloc-signature-simple { margin-top: 20px; font-size: 9.5pt; text-align: right; }
  .signatures-deux-colonnes { display: flex; justify-content: space-between; margin-top: 30px; font-weight: 700; text-align: left; }
  .ligne-identifiants { margin-bottom: 8px; font-size: 9pt; }
  table.bloc-libre { width: 100%; margin-bottom: 8px; font-size: 9pt; }
  table.bloc-libre td { padding: 3px 4px; vertical-align: top; }
  .ligne-dates { font-size: 9pt; margin-bottom: 10px; font-weight: 600; }
  table.tableau-garanties { width: 100%; border-collapse: collapse; border: 1px solid #64748b; margin-bottom: 14px; }
  table.tableau-garanties td { border: 1px solid #cbd5e1; padding: 4px 6px; font-size: 7.8pt; text-align: center; }
  table.recap-vertical { border: 1px solid #64748b; padding: 4px; font-size: 9.5pt; }
  table.recap-vertical td { padding: 3px 10px; }
  table.recap-vertical td.label { font-weight: 700; }
  .facture-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 24px; }
  .barcode-block img { height: 46px; }
  .barcode-ref { font-size: 7.5pt; color: #475569; margin-top: 2px; }
  .footer-logo-oreole { height: 22px; opacity: 0.85; }
  .titre-cp { text-align: center; font-weight: 800; font-size: 12pt; text-transform: uppercase; margin-bottom: 10px; line-height: 1.5; }
  table.cp-info td.label { font-weight: 600; color: #475569; background: #f8fafc; white-space: nowrap; }
  table.cp-garanties td { font-size: 7.5pt; }
  table.cp-recap { width: 290px; margin-top: 4px; }
  .cp-entete { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .cp-entete-logos { flex: 1; }
  .cp-tampon { border: 2px solid #4338ca; color: #4338ca; font-weight: 800; font-size: 10pt; text-align: center; padding: 4px 10px; line-height: 1.25; letter-spacing: 0.04em; }
  .cp-deux-blocs { display: flex; gap: 10px; align-items: stretch; }
  .cp-deux-blocs table { flex: 1; margin-bottom: 8px; }
  table.cp-bloc-client td.label, table.cp-bloc-police td.label { width: 78px; }
  table.cp-garanties td.g-lib { text-align: left; }
  table.cp-garanties td.g-num { text-align: right; white-space: nowrap; }
  table.cp-garanties tr.ligne-total td { background: #f1f5f9; }
  .cp-securite { font-size: 9pt; margin: 4px 0; }
  .cp-bas { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-top: 10px; }
  .cp-mentions { flex: 1; font-size: 9pt; }
  .cp-visa { color: #475569; margin-top: 6px; }
  table.cp-recap td.label { font-weight: 600; }
  @media print { .no-print { display: none !important; } }
`;

const openPrintWindow = (title, bodyHtml) => {
  const docHtml = `
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <title>${title}</title>
  <style>${PRINT_STYLES}</style>
</head>
<body>
  ${bodyHtml}
  <script>
    window.onload = function() { setTimeout(function() { window.print(); }, 400); };
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
};

/**
 * Ouvre une fenêtre d'impression dédiée pour un devis, avec la mise en page
 * fidèle aux 3 gabarits URANUS (Auto / IA-Voyage-Transport-Santé / MRH),
 * logos OREOLE + compagnie et code-barres (Auto uniquement, comme dans les
 * documents sources).
 */
export const printQuoteFacture = (quote) => {
  if (!quote) return;
  const branche = String(quote.branche || quote.produit || '').toLowerCase();
  let bodyHtml;
  if (branche.includes('auto')) {
    bodyHtml = buildAutoFacture(quote);
  } else if (branche.includes('mrh') || branche.includes('habit')) {
    bodyHtml = buildMrhFacture(quote);
  } else {
    bodyHtml = buildSimpleFacture(quote);
  }
  openPrintWindow(quote.numerodevis || 'Devis', bodyHtml);
};

/**
 * Ouvre une fenêtre d'impression pour les Conditions Particulières (échéancier
 * de police détaillé : véhicule + tableau des garanties), distinctes de la
 * facture proforma. Mise en page vérifiée sur un exemplaire réel Auto NSIA
 * (CONDITIONS PARTICULIERES ASSURANCE AUTO.pdf). Pour les autres branches,
 * faute d'un exemplaire de référence lisible, on réutilise la même charte
 * graphique avec les champs génériques disponibles.
 */
export const printConditionsParticulieres = (quote) => {
  if (!quote) return;
  // Un seul gabarit vérifié (Auto) pour l'instant ; réutilisé pour les autres
  // branches en l'absence d'un exemplaire de référence Conditions
  // Particulières lisible pour IA/Voyage/MRH/Transport/Santé.
  const bodyHtml = buildConditionsParticulieresAuto(quote);
  openPrintWindow(`CP-${quote.numerodevis || 'Devis'}`, bodyHtml);
};


/**
 * Impression Spécialisée et Conforme OREOLE pour les États Décisionnels
 * Adapte automatiquement les colonnes, les regroupements et les totaux selon l'état.
 */
export const printEtatDecisionnelDocument = ({
  etat,
  dateDebut,
  dateFin,
  typeEtat = 2,
  dossiers = [],
}) => {
  if (!etat) return;
  const code = (etat.code_etat || '').toUpperCase().trim();
  const libelle = (etat.libelle_etat || '').trim();
  const typeLabel = Number(typeEtat) === 1 ? 'BORDEREAU' : 'RÉCAPITULATIF';
  
  const isCommission = code.includes('03') || code.includes('04') || libelle.toLowerCase().includes('commission');
  const isEncaissement = code.includes('05') || code.includes('06') || libelle.toLowerCase().includes('encaissement');
  const isArriere = code.includes('07') || code.includes('08') || libelle.toLowerCase().includes('arriéré') || libelle.toLowerCase().includes('arriere');
  const isCimaE1 = code === 'E01' || code === 'E1' || libelle.toLowerCase().includes('cima e1');
  const isCimaE2 = code === 'E02' || code === 'E2' || libelle.toLowerCase().includes('cima e2');

  // Définition dynamique des colonnes selon la nature de l'état
  let columnHeaders = [];
  if (isCommission) {
    columnHeaders = [
      'N° Police', 'N° Quittance', 'N° Avenant', 'Date Émis.', 'Date Effet', 'Date Exp.',
      'Prime Nette', 'Accessoire', 'Taxe', 'Prime TTC', 'Acc. Interm.', 'Comm. Interm.'
    ];
  } else if (isEncaissement) {
    columnHeaders = [
      'N° Police', 'N° Quittance', 'N° Avenant', 'Date Émis.', 'Date Effet', 'Date Exp.',
      'Prime Nette', 'Accessoire', 'Taxe', 'Prime TTC', 'Montant Encaissé', 'Comm. Interm.'
    ];
  } else if (isArriere) {
    columnHeaders = [
      'N° Police', 'N° Quittance', 'N° Avenant', 'Date Émis.', 'Date Effet', 'Date Exp.',
      'Prime Nette', 'Accessoire', 'Taxe', 'Prime TTC', 'Montant Arriéré', 'Comm. Interm.'
    ];
  } else {
    // Émissions standard (C01, C02, D01, D02)
    columnHeaders = [
      'N° Police', 'N° Quittance', 'N° Avenant', 'Date Émis.', 'Date Effet', 'Date Exp.',
      'Prime Nette', 'Accessoire', 'Taxe', 'Prime TTC', 'Comm. Interm.'
    ];
  }

  const fmtMoney = (v) => Math.round(Number(v || 0)).toLocaleString('fr-FR');
  const fmtDate = (v) => {
    if (!v) return '-';
    const d = new Date(v);
    return isNaN(d.getTime()) ? String(v) : d.toLocaleDateString('fr-FR');
  };

  // Construction de la structure hiérarchique Compagnie > Client > Branche
  const groups = {};
  const grandTotal = {
    primeNette: 0,
    accessoire: 0,
    taxe: 0,
    primeTtc: 0,
    extra: 0,
    commission: 0,
  };

  dossiers.forEach((d) => {
    const cie = d.nom_compagnie || 'Compagnie non spécifiée';
    const cli = d.nom_client || 'Client Inconnu';
    const prod = d.libelle_produit || d.produit || 'Branche Principale';

    if (!groups[cie]) {
      groups[cie] = {
        nom_compagnie: cie,
        clients: {},
        total: { primeNette: 0, accessoire: 0, taxe: 0, primeTtc: 0, extra: 0, commission: 0 },
      };
    }

    if (!groups[cie].clients[cli]) {
      groups[cie].clients[cli] = {
        nom_client: cli,
        produits: {},
        total: { primeNette: 0, accessoire: 0, taxe: 0, primeTtc: 0, extra: 0, commission: 0 },
      };
    }

    if (!groups[cie].clients[cli].produits[prod]) {
      groups[cie].clients[cli].produits[prod] = {
        libelle_produit: prod,
        items: [],
        total: { primeNette: 0, accessoire: 0, taxe: 0, primeTtc: 0, extra: 0, commission: 0 },
      };
    }

    const pNette = Number(d.prime_nette || 0);
    const acc = Number(d.accessoire || 0);
    const tx = Number(d.taxe || 0);
    const pTtc = Number(d.prime_ttc || 0);
    const com = Number(d.commission_intermediaire || 0);
    const extraVal = isCommission
      ? Number(d.accessoire_intermediaire || 0)
      : isEncaissement
      ? Number(d.montant_encaissement || 0)
      : isArriere
      ? Number(d.montant_arriere || 0)
      : 0;

    // Totaux Produit
    groups[cie].clients[cli].produits[prod].total.primeNette += pNette;
    groups[cie].clients[cli].produits[prod].total.accessoire += acc;
    groups[cie].clients[cli].produits[prod].total.taxe += tx;
    groups[cie].clients[cli].produits[prod].total.primeTtc += pTtc;
    groups[cie].clients[cli].produits[prod].total.extra += extraVal;
    groups[cie].clients[cli].produits[prod].total.commission += com;

    // Totaux Client
    groups[cie].clients[cli].total.primeNette += pNette;
    groups[cie].clients[cli].total.accessoire += acc;
    groups[cie].clients[cli].total.taxe += tx;
    groups[cie].clients[cli].total.primeTtc += pTtc;
    groups[cie].clients[cli].total.extra += extraVal;
    groups[cie].clients[cli].total.commission += com;

    // Totaux Compagnie
    groups[cie].total.primeNette += pNette;
    groups[cie].total.accessoire += acc;
    groups[cie].total.taxe += tx;
    groups[cie].total.primeTtc += pTtc;
    groups[cie].total.extra += extraVal;
    groups[cie].total.commission += com;

    // Grand Total
    grandTotal.primeNette += pNette;
    grandTotal.accessoire += acc;
    grandTotal.taxe += tx;
    grandTotal.primeTtc += pTtc;
    grandTotal.extra += extraVal;
    grandTotal.commission += com;

    groups[cie].clients[cli].produits[prod].items.push(d);
  });

  const numCols = columnHeaders.length;

  const buildTableHtml = () => {
    let rowsHtml = '';

    // En-têtes de colonnes
    const ths = columnHeaders
      .map((col, idx) => `<th style="padding:6px 8px;border:0.5px solid #475569;background:#1e293b;color:#fff;font-size:7.5pt;text-align:${idx >= 6 ? 'right' : 'left'};text-transform:uppercase;">${col}</th>`)
      .join('');

    rowsHtml += `<thead><tr>${ths}</tr></thead><tbody>`;

    Object.keys(groups).forEach((cieName) => {
      const cie = groups[cieName];
      rowsHtml += `<tr><td colspan="${numCols}" style="padding:6px 8px;background:#e2e8f0;color:#0f172a;font-weight:800;font-size:8.5pt;border:0.5px solid #94a3b8;">COMPAGNIE : ${cie.nom_compagnie}</td></tr>`;

      Object.keys(cie.clients).forEach((cliName) => {
        const cli = cie.clients[cliName];
        rowsHtml += `<tr><td colspan="${numCols}" style="padding:5px 8px;background:#f1f5f9;color:#1e293b;font-weight:700;font-size:8pt;border:0.5px solid #cbd5e1;padding-left:16px;">CLIENT : ${cli.nom_client}</td></tr>`;

        Object.keys(cli.produits).forEach((prodName) => {
          const prod = cli.produits[prodName];
          rowsHtml += `<tr><td colspan="${numCols}" style="padding:4px 8px;background:#ffffff;color:#475569;font-weight:600;font-size:7.8pt;border:0.5px solid #e2e8f0;padding-left:28px;">BRANCHE : ${prod.libelle_produit}</td></tr>`;

          prod.items.forEach((item) => {
            rowsHtml += `<tr>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;font-family:monospace;">${item.numero_police || '-'}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;font-family:monospace;">${item.numero_quittance || '-'}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;">${item.numero_avenant || '-'}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;">${fmtDate(item.date_emission)}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;">${fmtDate(item.date_effet)}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;">${fmtDate(item.date_expiration)}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;text-align:right;">${fmtMoney(item.prime_nette)}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;text-align:right;">${fmtMoney(item.accessoire)}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;text-align:right;">${fmtMoney(item.taxe)}</td>
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;text-align:right;font-weight:700;">${fmtMoney(item.prime_ttc)}</td>
              ${isCommission || isEncaissement || isArriere ? `<td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;text-align:right;">${fmtMoney(isCommission ? item.accessoire_intermediaire : isEncaissement ? item.montant_encaissement : item.montant_arriere)}</td>` : ''}
              <td style="padding:3px 6px;border:0.5px solid #cbd5e1;font-size:7.5pt;text-align:right;color:#6366f1;font-weight:600;">${fmtMoney(item.commission_intermediaire)}</td>
            </tr>`;
          });

          // Sous-total Branche
          rowsHtml += `<tr style="background:#D6E3EC;font-weight:700;font-size:7.8pt;">
            <td colspan="6" style="padding:4px 8px;border:0.5px solid #94a3b8;padding-left:28px;">TOTAL ${prod.libelle_produit}</td>
            <td style="padding:4px 6px;border:0.5px solid #94a3b8;text-align:right;">${fmtMoney(prod.total.primeNette)}</td>
            <td style="padding:4px 6px;border:0.5px solid #94a3b8;text-align:right;">${fmtMoney(prod.total.accessoire)}</td>
            <td style="padding:4px 6px;border:0.5px solid #94a3b8;text-align:right;">${fmtMoney(prod.total.taxe)}</td>
            <td style="padding:4px 6px;border:0.5px solid #94a3b8;text-align:right;">${fmtMoney(prod.total.primeTtc)}</td>
            ${isCommission || isEncaissement || isArriere ? `<td style="padding:4px 6px;border:0.5px solid #94a3b8;text-align:right;">${fmtMoney(prod.total.extra)}</td>` : ''}
            <td style="padding:4px 6px;border:0.5px solid #94a3b8;text-align:right;">${fmtMoney(prod.total.commission)}</td>
          </tr>`;
        });

        // Sous-total Client
        rowsHtml += `<tr style="background:#cbd5e1;font-weight:800;font-size:8pt;">
          <td colspan="6" style="padding:4px 8px;border:0.5px solid #64748b;padding-left:16px;">TOTAL ${cli.nom_client}</td>
          <td style="padding:4px 6px;border:0.5px solid #64748b;text-align:right;">${fmtMoney(cli.total.primeNette)}</td>
          <td style="padding:4px 6px;border:0.5px solid #64748b;text-align:right;">${fmtMoney(cli.total.accessoire)}</td>
          <td style="padding:4px 6px;border:0.5px solid #64748b;text-align:right;">${fmtMoney(cli.total.taxe)}</td>
          <td style="padding:4px 6px;border:0.5px solid #64748b;text-align:right;">${fmtMoney(cli.total.primeTtc)}</td>
          ${isCommission || isEncaissement || isArriere ? `<td style="padding:4px 6px;border:0.5px solid #64748b;text-align:right;">${fmtMoney(cli.total.extra)}</td>` : ''}
          <td style="padding:4px 6px;border:0.5px solid #64748b;text-align:right;">${fmtMoney(cli.total.commission)}</td>
        </tr>`;
      });

      // Sous-total Compagnie
      rowsHtml += `<tr style="background:#94a3b8;color:#0f172a;font-weight:900;font-size:8.2pt;">
        <td colspan="6" style="padding:5px 8px;border:0.5px solid #475569;">TOTAL ${cie.nom_compagnie}</td>
        <td style="padding:5px 6px;border:0.5px solid #475569;text-align:right;">${fmtMoney(cie.total.primeNette)}</td>
        <td style="padding:5px 6px;border:0.5px solid #475569;text-align:right;">${fmtMoney(cie.total.accessoire)}</td>
        <td style="padding:5px 6px;border:0.5px solid #475569;text-align:right;">${fmtMoney(cie.total.taxe)}</td>
        <td style="padding:5px 6px;border:0.5px solid #475569;text-align:right;">${fmtMoney(cie.total.primeTtc)}</td>
        ${isCommission || isEncaissement || isArriere ? `<td style="padding:5px 6px;border:0.5px solid #475569;text-align:right;">${fmtMoney(cie.total.extra)}</td>` : ''}
        <td style="padding:5px 6px;border:0.5px solid #475569;text-align:right;">${fmtMoney(cie.total.commission)}</td>
      </tr>`;
    });

    // Total Général (Exact look OREOLE #284962)
    rowsHtml += `<tr style="background:#284962;color:#ffffff;font-weight:900;font-size:8.5pt;">
      <td colspan="6" style="padding:6px 8px;border:0.5px solid #0f172a;">TOTAL GÉNÉRAL (${dossiers.length} lignes)</td>
      <td style="padding:6px 6px;border:0.5px solid #0f172a;text-align:right;">${fmtMoney(grandTotal.primeNette)}</td>
      <td style="padding:6px 6px;border:0.5px solid #0f172a;text-align:right;">${fmtMoney(grandTotal.accessoire)}</td>
      <td style="padding:6px 6px;border:0.5px solid #0f172a;text-align:right;">${fmtMoney(grandTotal.taxe)}</td>
      <td style="padding:6px 6px;border:0.5px solid #0f172a;text-align:right;">${fmtMoney(grandTotal.primeTtc)}</td>
      ${isCommission || isEncaissement || isArriere ? `<td style="padding:6px 6px;border:0.5px solid #0f172a;text-align:right;">${fmtMoney(grandTotal.extra)}</td>` : ''}
      <td style="padding:6px 6px;border:0.5px solid #0f172a;text-align:right;">${fmtMoney(grandTotal.commission)}</td>
    </tr>`;

    rowsHtml += '</tbody>';
    return rowsHtml;
  };

  const docHtml = `
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <title>${typeLabel} : ${libelle}</title>
  <style>
    @page {
      size: A4 landscape;
      margin: 8mm 10mm;
    }
    body {
      font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
      color: #0f172a;
      background: #ffffff;
      margin: 0;
      padding: 0;
      font-size: 8pt;
      line-height: 1.3;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    .header-table {
      width: 100%;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 6px;
      margin-bottom: 8px;
    }
    .republic-text {
      font-size: 6.8pt;
      font-weight: 800;
      letter-spacing: 0.8px;
      color: #475569;
      text-transform: uppercase;
    }
    .cabinet-title {
      font-size: 11pt;
      font-weight: 900;
      color: #0f172a;
      margin: 2px 0;
    }
    .cabinet-sub {
      font-size: 7pt;
      color: #64748b;
    }
    .title-banner {
      background: #284962;
      color: #ffffff;
      text-align: center;
      padding: 6px 10px;
      border-radius: 4px;
      margin-bottom: 8px;
    }
    .title-main {
      font-size: 9.5pt;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .title-sub {
      font-size: 7.2pt;
      opacity: 0.9;
      margin-top: 2px;
    }
    .kpi-grid {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }
    .kpi-card {
      flex: 1;
      border: 0.5px solid #cbd5e1;
      background: #f8fafc;
      padding: 4px 8px;
      border-radius: 4px;
      text-align: center;
    }
    .kpi-label {
      font-size: 6.2pt;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
    }
    .kpi-val {
      font-size: 8.5pt;
      font-weight: 800;
      color: #0f172a;
      margin-top: 1px;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 8px;
    }
    table.data-table th, table.data-table td {
      border: 0.5px solid #cbd5e1;
    }
    .legal-notice {
      background: #f8fafc;
      border: 0.5px solid #cbd5e1;
      padding: 5px 8px;
      border-radius: 4px;
      font-size: 6.8pt;
      color: #334155;
      margin-top: 6px;
    }
    .signatures {
      display: flex;
      justify-content: space-between;
      margin-top: 12px;
      font-size: 7.5pt;
    }
    .sig-block {
      width: 250px;
    }
    .sig-space {
      height: 40px;
      border-bottom: 1px dotted #94a3b8;
      margin-top: 4px;
    }
    @media print {
      .no-print { display: none !important; }
    }
  </style>
</head>
<body>
  <table class="header-table">
    <tr>
      <td style="vertical-align:top;">
        <div class="republic-text">RÉPUBLIQUE DE CÔTE D'IVOIRE • MINISTÈRE DE L'ÉCONOMIE ET DES FINANCES</div>
        <div class="cabinet-title">LE PHARE COURTAGE & GESTION D'ASSURANCES</div>
        <div class="cabinet-sub">Agrément N° 0021 / MEF / DAPS • Siège Social : Abidjan Plateau • Code CIMA CRCA</div>
      </td>
      <td style="vertical-align:top;text-align:right;">
        <div style="font-size:7pt;color:#64748b;">Édition du : <strong>${new Date().toLocaleDateString('fr-FR')} à ${new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</strong></div>
        <div style="font-size:7.5pt;font-weight:800;color:#0284c7;margin-top:2px;">DOCUMENT OFFICIEL CERTIFIÉ</div>
        <div style="font-size:6.8pt;color:#64748b;">Code État : <strong>${code}</strong></div>
      </td>
    </tr>
  </table>

  <div class="title-banner">
    <div class="title-main">${typeLabel} : ${libelle}</div>
    <div class="title-sub">Période du ${dateDebut} au ${dateFin} • Procédure Postgres fn_bordereau_recap_emission</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Total Quittances</div>
      <div class="kpi-val" style="color:#0284c7;">${dossiers.length.toLocaleString('fr-FR')}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Prime Nette Totale</div>
      <div class="kpi-val">${fmtMoney(grandTotal.primeNette)} F</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Accessoires Totaux</div>
      <div class="kpi-val">${fmtMoney(grandTotal.accessoire)} F</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Taxes Totales</div>
      <div class="kpi-val">${fmtMoney(grandTotal.taxe)} F</div>
    </div>
    <div class="kpi-card" style="background:#ecfdf5;border-color:#a7f3d0;">
      <div class="kpi-label" style="color:#059669;">Prime TTC Totale</div>
      <div class="kpi-val" style="color:#059669;">${fmtMoney(grandTotal.primeTtc)} F</div>
    </div>
    <div class="kpi-card" style="background:#f5f3ff;border-color:#ddd6fe;">
      <div class="kpi-label" style="color:#7c3aed;">Commissions Totales</div>
      <div class="kpi-val" style="color:#7c3aed;">${fmtMoney(grandTotal.commission)} F</div>
    </div>
  </div>

  <table class="data-table">
    ${buildTableHtml()}
  </table>

  <div class="legal-notice">
    <strong>Attestation de Contrôle & Conformité Fiscale :</strong> Le présent bordereau récapitulatif consolide l'ensemble des émissions de polices, quittances et taxes réglementaires conformément aux dispositions des Articles 13 et suivants du Code CIMA.
  </div>

  <div class="signatures">
    <div class="sig-block">
      <div style="font-weight:700;color:#334155;">Le Chef de Service Comptabilité & Reporting :</div>
      <div class="sig-space"></div>
    </div>
    <div class="sig-block" style="text-align:right;">
      <div style="font-weight:700;color:#334155;">Pour la Direction Générale / Visa CIMA :</div>
      <div class="sig-space" style="color:#0284c7;font-weight:700;">[ Cachet Officiel ]</div>
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

  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(docHtml);
    printWindow.document.close();
  }
};
