'use client';

import type { IconButtonProps } from '@mui/material/IconButton';

import { m } from 'framer-motion';
import { useCallback } from 'react';

import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import { useColorScheme } from '@mui/material/styles';

import { Iconify } from 'src/components/iconify';
import { useSettingsContext } from 'src/components/settings';
import { varTap, varHover, transitionTap } from 'src/components/animate';

// ----------------------------------------------------------------------

export function ThemeToggleButton({ sx, ...other }: IconButtonProps) {
  const settings = useSettingsContext();
  const { setMode } = useColorScheme();

  const isDark = settings.state.mode === 'dark';

  const handleToggle = useCallback(() => {
    const newMode = isDark ? 'light' : 'dark';
    setMode(newMode);
    settings.setField('mode', newMode);
  }, [isDark, setMode, settings]);

  return (
    <Tooltip title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}>
      <IconButton
        component={m.button}
        whileTap={varTap(0.96)}
        whileHover={varHover(1.04)}
        transition={transitionTap()}
        aria-label="Toggle theme"
        onClick={handleToggle}
        sx={[
          (theme) => ({
            p: 0,
            width: 40,
            height: 40,
          }),
          ...(Array.isArray(sx) ? sx : [sx]),
        ]}
        {...other}
      >
        <Iconify
          icon={isDark ? 'solar:sun-bold-duotone' : 'solar:moon-bold-duotone'}
          width={24}
        />
      </IconButton>
    </Tooltip>
  );
}

