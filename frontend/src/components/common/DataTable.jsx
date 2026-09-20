import { LoadingSpinner } from './LoadingSpinner';
import React, { useState, useMemo } from 'react';
import { Search, ChevronLeft, ChevronRight, Inbox, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';

export const DataTable = ({
  columns = [],
  data = [],
  loading = false,
  loadingText = 'Chargement des donn?es en cours...',
  searchable = true,
  searchPlaceholder = 'Rechercher un élément...',
  itemsPerPage = 10,
  actions,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState({ index: null, direction: 'asc' });

  // Filter data based on search term (Optimized for speed on large datasets)
  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return data;
    const term = searchTerm.toLowerCase().trim();
    return data.filter((row) => {
      // Prioritize primary searchable columns
      const name = String(row.nomcomplet || row.nom || row.Nom || row.client_nom || row.numeropolice || row.numerodevis || '').toLowerCase();
      if (name.includes(term)) return true;
      const code = String(row.codeclient || row.Matricule || row.police || row.numeroquittance || '').toLowerCase();
      if (code.includes(term)) return true;
      const contact = String(row.telephone || row.Mobile || row.Telephone || row.email || '').toLowerCase();
      if (contact.includes(term)) return true;
      return false;
    });
  }, [data, searchTerm]);

  const getSortValue = (col, row) => {
    if (col.sortAccessor) return col.sortAccessor(row);
    if (col.accessor) return row[col.accessor];
    return '';
  };

  const sortedData = useMemo(() => {
    if (sortConfig.index === null) return filteredData;
    const col = columns[sortConfig.index];
    if (!col) return filteredData;
    const dir = sortConfig.direction === 'asc' ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const va = getSortValue(col, a);
      const vb = getSortValue(col, b);
      if (va == null && vb == null) return 0;
      if (va == null) return -1 * dir;
      if (vb == null) return 1 * dir;
      const na = Number(va);
      const nb = Number(vb);
      if (!isNaN(na) && !isNaN(nb) && va !== '' && vb !== '') {
        return (na - nb) * dir;
      }
      const sa = String(va).toLowerCase();
      const sb = String(vb).toLowerCase();
      return sa.localeCompare(sb, 'fr', { numeric: true }) * dir;
    });
  }, [filteredData, sortConfig, columns]);

  const handleSort = (colIdx) => {
    const col = columns[colIdx];
    if (!col || !col.sortable) return;
    setSortConfig((prev) => {
      if (prev.index === colIdx) {
        return { index: colIdx, direction: prev.direction === 'asc' ? 'desc' : 'asc' };
      }
      return { index: colIdx, direction: 'asc' };
    });
    setCurrentPage(1);
  };

  // Pagination calculation
  const totalPages = Math.ceil(sortedData.length / itemsPerPage) || 1;
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return sortedData.slice(start, start + itemsPerPage);
  }, [sortedData, currentPage, itemsPerPage]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      {/* Search & Header Actions */}
      {(searchable || actions) && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
          {searchable && (
            <div style={{ position: 'relative', width: '100%', maxWidth: '340px' }}>
              <Search
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)' }}
              />
              <input
                type="text"
                className="form-control"
                style={{ paddingLeft: '2.5rem' }}
                placeholder={searchPlaceholder}
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
              />
            </div>
          )}

          {actions && <div style={{ display: 'flex', gap: '0.5rem' }}>{actions}</div>}
        </div>
      )}

      {/* Table Content */}
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col, idx) => {
                const isSorted = sortConfig.index === idx;
                return (
                  <th
                    key={idx}
                    style={{
                      textAlign: col.align || 'left',
                      width: col.width,
                      cursor: col.sortable ? 'pointer' : 'default',
                      userSelect: 'none',
                    }}
                    onClick={() => handleSort(idx)}
                    title={col.sortable ? 'Cliquer pour trier' : undefined}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      {col.header}
                      {col.sortable && (
                        isSorted ? (
                          sortConfig.direction === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                        ) : (
                          <ArrowUpDown size={12} style={{ opacity: 0.4 }} />
                        )
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <LoadingSpinner text={loadingText} size={32} />
                </td>
              </tr>
            ) : paginatedData.length > 0 ? (
              paginatedData.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} style={{ textAlign: col.align || 'left' }}>
                      {col.render ? col.render(row) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} style={{ textAlign: 'center', padding: '3.5rem 1rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                    <Inbox size={36} color="var(--text-muted)" />
                    <p style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Aucun enregistrement trouvé</p>
                    <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                      {searchTerm ? 'Essayez de modifier votre terme de recherche' : 'Cette section ne contient pas encore de données'}
                    </p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {sortedData.length > itemsPerPage && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
          <span>
            Affichage de <strong>{(currentPage - 1) * itemsPerPage + 1}</strong> à{' '}
            <strong>{Math.min(currentPage * itemsPerPage, sortedData.length)}</strong> sur{' '}
            <strong>{sortedData.length}</strong> lignes
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.6rem' }}
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            >
              <ChevronLeft size={16} />
            </button>
            <span>Page {currentPage} / {totalPages}</span>
            <button
              className="btn btn-secondary"
              style={{ padding: '0.35rem 0.6rem' }}
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataTable;
