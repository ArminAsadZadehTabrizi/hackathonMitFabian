'use client';

import type {
  GridColDef,
  GridRowSelectionModel,
  GridColumnVisibilityModel,
} from '@mui/x-data-grid';
import type { IReceiptItem, IReceiptTableFilters } from 'src/types/receipt';

import { useBoolean, useSetState } from 'minimal-shared/hooks';
import { useMemo, useState, useEffect, useCallback } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Button from '@mui/material/Button';
import { useTheme } from '@mui/material/styles';
import { DataGrid, gridClasses } from '@mui/x-data-grid';

import { paths } from 'src/routes/paths';

import { useGetReceipts } from 'src/actions/receipt';
import { DashboardContent } from 'src/layouts/dashboard';

import { toast } from 'src/components/snackbar';
import { Iconify } from 'src/components/iconify';
import { EmptyContent } from 'src/components/empty-content';
import { ConfirmDialog } from 'src/components/custom-dialog';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';
import { useToolbarSettings, CustomGridActionsCellItem } from 'src/components/custom-data-grid';

import { ReceiptTableToolbar } from '../receipt-table-toolbar';
import { ReceiptUploadZone } from '../components/receipt-upload-zone';
import {
  RenderCellVAT,
  RenderCellDate,
  RenderCellTotal,
  RenderCellStatus,
  RenderCellReceipt,
  RenderCellCategory,
  RenderCellAuditFlags,
} from '../receipt-table-row';

// ----------------------------------------------------------------------

const HIDE_COLUMNS = { category: false };
const HIDE_COLUMNS_TOGGLABLE = ['category', 'actions'];

// ----------------------------------------------------------------------

export function ReceiptListView() {
  const confirmDialog = useBoolean();
  const toolbarOptions = useToolbarSettings();
  const { receipts, receiptsLoading } = useGetReceipts();

  const [tableData, setTableData] = useState<IReceiptItem[]>([]);

  const [selectedRows, setSelectedRows] = useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set(),
  });

  const filters = useSetState<IReceiptTableFilters>({
    vendor: '',
    category: '',
    startDate: null,
    endDate: null,
    status: '',
  });

  const [columnVisibilityModel, setColumnVisibilityModel] =
    useState<GridColumnVisibilityModel>(HIDE_COLUMNS);

  useEffect(() => {
    setTableData(receipts);
  }, [receipts]);

  const categories = useMemo(() => {
    const cats = new Set(receipts.map((r) => r.category));
    return Array.from(cats).sort();
  }, [receipts]);

  const vendors = useMemo(() => {
    const vends = new Set(receipts.map((r) => r.vendor));
    return Array.from(vends).sort();
  }, [receipts]);

  const canReset =
    filters.state.vendor !== '' ||
    filters.state.category !== '' ||
    filters.state.startDate !== null ||
    filters.state.endDate !== null ||
    filters.state.status !== '';

  const dataFiltered = useMemo(() => {
    let filtered = tableData;

    if (filters.state.vendor) {
      filtered = filtered.filter((r) => r.vendor === filters.state.vendor);
    }
    if (filters.state.category) {
      filtered = filtered.filter((r) => r.category === filters.state.category);
    }
    if (filters.state.status) {
      filtered = filtered.filter((r) => r.status === filters.state.status);
    }
    if (filters.state.startDate) {
      filtered = filtered.filter((r) => new Date(r.date) >= filters.state.startDate!);
    }
    if (filters.state.endDate) {
      filtered = filtered.filter((r) => new Date(r.date) <= filters.state.endDate!);
    }

    return filtered;
  }, [tableData, filters.state]);

  const handleDeleteRow = useCallback((id: string) => {
    setTableData((prev) => prev.filter((row) => (row.id || row.receiptNumber) !== id));
    toast.success('Delete success!');
  }, []);

  const handleDeleteRows = useCallback(() => {
    setTableData((prev) => prev.filter((row) => !selectedRows.ids.has(row.id || row.receiptNumber)));
    toast.success('Delete success!');
  }, [selectedRows.ids]);

  const columns = useGetColumns({ onDeleteRow: handleDeleteRow });

  const renderConfirmDialog = () => (
    <ConfirmDialog
      open={confirmDialog.value}
      onClose={confirmDialog.onFalse}
      title="Delete"
      content={
        <>
          Are you sure want to delete <strong> {selectedRows.ids.size} </strong> items?
        </>
      }
      action={
        <Button
          variant="contained"
          color="error"
          onClick={() => {
            handleDeleteRows();
            confirmDialog.onFalse();
          }}
        >
          Delete
        </Button>
      }
    />
  );

  return (
    <>
      <DashboardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <CustomBreadcrumbs
          heading="Receipts"
          links={[
            { name: 'Dashboard', href: paths.dashboard.root },
            { name: 'Receipts' },
          ]}
          action={
            <Button
              variant="contained"
              startIcon={<Iconify icon="mingcute:add-line" />}
              disabled
            >
              Upload Receipt
            </Button>
          }
          sx={{ mb: { xs: 3, md: 5 } }}
        />

        <Box sx={{ mb: 3 }}>
          <ReceiptUploadZone
            onUpload={async (files) => {
              // Simulate upload - replace with actual API call
              console.log('Uploading files:', files);
              toast.success(`Uploading ${files.length} file(s)...`);
            }}
          />
        </Box>

        <Card
          sx={{
            minHeight: 640,
            flexGrow: { md: 1 },
            display: { md: 'flex' },
            height: { xs: 800, md: '1px' },
            flexDirection: { md: 'column' },
          }}
        >
          <DataGrid
            {...toolbarOptions.settings}
            checkboxSelection
            disableRowSelectionOnClick
            rows={dataFiltered}
            columns={columns}
            loading={receiptsLoading}
            getRowId={(row) => row.id || row.receiptNumber}
            getRowHeight={() => 'auto'}
            pageSizeOptions={[5, 10, 20, { value: -1, label: 'All' }]}
            initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
            columnVisibilityModel={columnVisibilityModel}
            onColumnVisibilityModelChange={(newModel) => setColumnVisibilityModel(newModel)}
            onRowSelectionModelChange={(newSelectionModel) => setSelectedRows(newSelectionModel)}
            slots={{
              noRowsOverlay: () => <EmptyContent />,
              noResultsOverlay: () => <EmptyContent title="No results found" />,
              toolbar: () => (
                <ReceiptTableToolbar
                  filters={filters}
                  canReset={canReset}
                  filteredResults={dataFiltered.length}
                  selectedRowCount={selectedRows.ids.size}
                  categories={categories}
                  vendors={vendors}
                  onOpenConfirmDeleteRows={confirmDialog.onTrue}
                  settings={toolbarOptions.settings}
                  onChangeSettings={toolbarOptions.onChangeSettings}
                />
              ),
            }}
            slotProps={{
              columnsManagement: {
                getTogglableColumns: () =>
                  columns
                    .filter((col) => !HIDE_COLUMNS_TOGGLABLE.includes(col.field))
                    .map((col) => col.field),
              },
            }}
            sx={{
              [`& .${gridClasses.cell}`]: {
                display: 'flex',
                alignItems: 'center',
              },
            }}
          />
        </Card>
      </DashboardContent>

      {renderConfirmDialog()}
    </>
  );
}

// ----------------------------------------------------------------------

type UseGetColumnsProps = {
  onDeleteRow: (id: string) => void;
};

const useGetColumns = ({ onDeleteRow }: UseGetColumnsProps) => {
  const theme = useTheme();

  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: 'receiptNumber',
        headerName: 'Receipt',
        flex: 1,
        minWidth: 280,
        hideable: false,
        renderCell: (params) => (
          <RenderCellReceipt
            params={params}
            href={paths.dashboard.receipt.details(params.row.id || params.row.receiptNumber)}
          />
        ),
      },
      {
        field: 'vendor',
        headerName: 'Vendor',
        width: 180,
      },
      {
        field: 'category',
        headerName: 'Category',
        width: 140,
        renderCell: (params) => <RenderCellCategory params={params} />,
      },
      {
        field: 'date',
        headerName: 'Date',
        width: 160,
        renderCell: (params) => <RenderCellDate params={params} />,
      },
      {
        field: 'total',
        headerName: 'Total',
        width: 120,
        renderCell: (params) => <RenderCellTotal params={params} />,
      },
      {
        field: 'vat',
        headerName: 'VAT',
        width: 120,
        renderCell: (params) => <RenderCellVAT params={params} />,
      },
      {
        field: 'paymentMethod',
        headerName: 'Payment',
        width: 120,
      },
      {
        field: 'status',
        headerName: 'Status',
        width: 120,
        renderCell: (params) => <RenderCellStatus params={params} />,
      },
      {
        field: 'auditFlags',
        headerName: 'Issues',
        width: 150,
        renderCell: (params) => <RenderCellAuditFlags params={params} />,
      },
      {
        type: 'actions',
        field: 'actions',
        headerName: ' ',
        width: 64,
        align: 'right',
        headerAlign: 'right',
        sortable: false,
        filterable: false,
        disableColumnMenu: true,
        getActions: (params) => [
          <CustomGridActionsCellItem
            showInMenu
            label="View"
            icon={<Iconify icon="solar:eye-bold" />}
            href={paths.dashboard.receipt.details(params.row.id || params.row.receiptNumber)}
          />,
          <CustomGridActionsCellItem
            showInMenu
            label="Delete"
            icon={<Iconify icon="solar:trash-bin-trash-bold" />}
            onClick={() => onDeleteRow(params.row.id || params.row.receiptNumber)}
            style={{ color: theme.vars.palette.error.main }}
          />,
        ],
      },
    ],
    [onDeleteRow, theme.vars.palette.error.main]
  );

  return columns;
};

