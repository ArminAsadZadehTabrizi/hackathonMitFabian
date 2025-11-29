import type { UseSetStateReturn } from 'minimal-shared/hooks';
import type { SelectChangeEvent } from '@mui/material/Select';
import type { IReceiptTableFilters } from 'src/types/receipt';
import type { CustomToolbarSettingsButtonProps } from 'src/components/custom-data-grid';

import { useState, useEffect, useCallback } from 'react';

import Button from '@mui/material/Button';
import Select from '@mui/material/Select';
import { Toolbar } from '@mui/x-data-grid';
import MenuItem from '@mui/material/MenuItem';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';

import { Iconify } from 'src/components/iconify';
import {
  ToolbarContainer,
  ToolbarLeftPanel,
  ToolbarRightPanel,
  CustomToolbarQuickFilter,
  CustomToolbarFilterButton,
  CustomToolbarExportButton,
  CustomToolbarColumnsButton,
  CustomToolbarSettingsButton,
} from 'src/components/custom-data-grid';

// ----------------------------------------------------------------------

type FilterOption = {
  value: string;
  label: string;
};

type Props = CustomToolbarSettingsButtonProps & {
  canReset: boolean;
  filteredResults: number;
  selectedRowCount: number;
  filters: UseSetStateReturn<IReceiptTableFilters>;
  categories: string[];
  vendors: string[];
  onOpenConfirmDeleteRows: () => void;
};

export function ReceiptTableToolbar({
  filters,
  canReset,
  filteredResults,
  selectedRowCount,
  categories,
  vendors,
  onOpenConfirmDeleteRows,
  settings,
  onChangeSettings,
}: Props) {
  const { state: currentFilters, setState: updateFilters } = filters;

  const [category, setCategory] = useState<string>('');
  const [vendor, setVendor] = useState<string>('');

  useEffect(() => {
    setCategory(currentFilters.category || '');
    setVendor(currentFilters.vendor || '');
  }, [currentFilters.category, currentFilters.vendor]);

  const handleSelect = useCallback(
    (setter: (value: string) => void, filterKey: keyof IReceiptTableFilters) =>
      (event: SelectChangeEvent<string>) => {
        const value = event.target.value;
        setter(value);
        updateFilters({ [filterKey]: value || '' });
      },
    [updateFilters]
  );

  const renderLeftPanel = () => (
    <>
      <FilterSelect
        label="Category"
        value={category}
        options={categories.map((cat) => ({ value: cat, label: cat }))}
        onChange={handleSelect(setCategory, 'category')}
      />

      <FilterSelect
        label="Vendor"
        value={vendor}
        options={vendors.map((vend) => ({ value: vend, label: vend }))}
        onChange={handleSelect(setVendor, 'vendor')}
      />

      <CustomToolbarQuickFilter />
    </>
  );

  const renderRightPanel = () => (
    <>
      {!!selectedRowCount && (
        <Button
          size="small"
          color="error"
          startIcon={<Iconify icon="solar:trash-bin-trash-bold" />}
          onClick={onOpenConfirmDeleteRows}
        >
          Delete ({selectedRowCount})
        </Button>
      )}

      <CustomToolbarColumnsButton />
      <CustomToolbarFilterButton />
      <CustomToolbarExportButton />
      <CustomToolbarSettingsButton settings={settings} onChangeSettings={onChangeSettings} />
    </>
  );

  return (
    <Toolbar>
      <ToolbarContainer>
        <ToolbarLeftPanel>{renderLeftPanel()}</ToolbarLeftPanel>
        <ToolbarRightPanel>{renderRightPanel()}</ToolbarRightPanel>
      </ToolbarContainer>
    </Toolbar>
  );
}

// ----------------------------------------------------------------------

type FilterSelectProps = {
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (event: SelectChangeEvent<string>) => void;
};

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  const id = `filter-${label.toLowerCase()}-select`;

  return (
    <FormControl sx={{ flexShrink: 0, width: { xs: 1, md: 200 } }}>
      <InputLabel htmlFor={id}>{label}</InputLabel>
      <Select
        label={label}
        value={value}
        onChange={onChange}
        inputProps={{ id }}
      >
        <MenuItem value="">
          <em>All</em>
        </MenuItem>
        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

