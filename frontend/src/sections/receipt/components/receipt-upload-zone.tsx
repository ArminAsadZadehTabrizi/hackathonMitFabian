'use client';

import { useCallback, useState } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import LinearProgress from '@mui/material/LinearProgress';

import { Iconify } from 'src/components/iconify';
import { useTranslate } from 'src/locales';

// ----------------------------------------------------------------------

type ReceiptUploadZoneProps = {
  onUpload?: (files: File[]) => void;
  disabled?: boolean;
};

export function ReceiptUploadZone({ onUpload, disabled }: ReceiptUploadZoneProps) {
  const { t } = useTranslate('common');
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled) return;

      const files = Array.from(e.dataTransfer.files).filter(
        (file) => file.type.startsWith('image/') || file.type === 'application/pdf'
      );

      if (files.length === 0) return;

      if (onUpload) {
        setIsProcessing(true);
        setUploadProgress(0);

        // Simulate upload progress
        const interval = setInterval(() => {
          setUploadProgress((prev) => {
            if (prev >= 90) {
              clearInterval(interval);
              return 90;
            }
            return prev + 10;
          });
        }, 200);

        try {
          await onUpload(files);
          setUploadProgress(100);
          setTimeout(() => {
            setIsProcessing(false);
            setUploadProgress(0);
          }, 500);
        } catch (error) {
          setIsProcessing(false);
          setUploadProgress(0);
        }
      }
    },
    [disabled, onUpload]
  );

  const handleFileInput = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files || disabled) return;

      const files = Array.from(e.target.files);

      if (files.length === 0) return;

      if (onUpload) {
        setIsProcessing(true);
        setUploadProgress(0);

        const interval = setInterval(() => {
          setUploadProgress((prev) => {
            if (prev >= 90) {
              clearInterval(interval);
              return 90;
            }
            return prev + 10;
          });
        }, 200);

        try {
          await onUpload(files);
          setUploadProgress(100);
          setTimeout(() => {
            setIsProcessing(false);
            setUploadProgress(0);
          }, 500);
        } catch (error) {
          setIsProcessing(false);
          setUploadProgress(0);
        }
      }
    },
    [disabled, onUpload]
  );

  return (
    <Card
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      sx={{
        p: 4,
        border: '2px dashed',
        borderColor: isDragging ? 'primary.main' : 'divider',
        bgcolor: isDragging ? 'action.hover' : 'background.paper',
        transition: 'all 0.2s ease-in-out',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {isProcessing && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 1,
          }}
        >
          <LinearProgress variant="determinate" value={uploadProgress} />
        </Box>
      )}

      <Stack spacing={3} alignItems="center" sx={{ py: 2 }}>
        <Box
          sx={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            bgcolor: isDragging ? 'primary.lighter' : 'background.neutral',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease-in-out',
          }}
        >
          <Iconify
            icon={isProcessing ? 'solar:file-check-bold-duotone' : 'solar:cloud-upload-bold-duotone'}
            width={40}
            sx={{ color: isDragging ? 'primary.main' : 'text.secondary' }}
          />
        </Box>

        <Box sx={{ textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            {isProcessing ? t('common.processing') : t('receipts.upload')}
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>
            {isDragging
              ? 'Drop files here'
              : 'Drag & drop receipt images here, or click to browse'}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.disabled', mt: 1, display: 'block' }}>
            Supports: JPG, PNG, PDF (Max 10MB per file)
          </Typography>
        </Box>

        <Button
          component="label"
          variant="contained"
          startIcon={<Iconify icon="solar:folder-with-files-bold-duotone" />}
          disabled={disabled || isProcessing}
          sx={{ mt: 2 }}
        >
          {isProcessing ? 'Processing...' : 'Browse Files'}
          <input
            type="file"
            hidden
            multiple
            accept="image/*,application/pdf"
            onChange={handleFileInput}
            disabled={disabled || isProcessing}
          />
        </Button>
      </Stack>
    </Card>
  );
}

