'use client';

import { useMemo, useState, useEffect } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Container from '@mui/material/Container';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';

import { fCurrency } from 'src/utils/format-number';

import { useGetReceipt } from 'src/actions/receipt';
import { DashboardContent } from 'src/layouts/dashboard';

import { Label } from 'src/components/label';
import { Iconify } from 'src/components/iconify';
import { EmptyContent } from 'src/components/empty-content';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';

// ----------------------------------------------------------------------

type Props = {
  id: string;
};

export function ReceiptDetailsView({ id }: Props) {
  const { receipt, receiptLoading } = useGetReceipt(id);
  const [mismatchExpanded, setMismatchExpanded] = useState(false);
  const [editedReceipt, setEditedReceipt] = useState<any>(null);

  // Initialize edited receipt when receipt loads
  useEffect(() => {
    if (receipt) {
      setEditedReceipt({
        vendor: receipt.vendor,
        date: receipt.date,
        total: receipt.total,
        vat: receipt.vat,
        category: receipt.category,
        paymentMethod: receipt.paymentMethod,
      });
    }
  }, [receipt]);

  const hasIssues = useMemo(() => {
    if (!receipt) return false;
    const { auditFlags } = receipt;
    return auditFlags.isDuplicate || auditFlags.hasTotalMismatch || auditFlags.missingVAT || !!auditFlags.suspiciousCategory;
  }, [receipt]);

  const mismatchDetails = useMemo(() => {
    if (!receipt || !receipt.auditFlags.hasTotalMismatch) return null;
    
    const expectedTotal = receipt.lineItems.reduce((sum, item) => sum + item.total, 0) + (receipt.vat || 0);
    const actualTotal = receipt.total;
    const difference = actualTotal - expectedTotal;
    
    return {
      expectedTotal,
      actualTotal,
      difference,
    };
  }, [receipt]);

  if (receiptLoading) {
    return (
      <DashboardContent>
        <Container>
          <Typography>Loading...</Typography>
        </Container>
      </DashboardContent>
    );
  }

  if (!receipt) {
    return (
      <DashboardContent>
        <Container>
          <EmptyContent title="Receipt not found" />
        </Container>
      </DashboardContent>
    );
  }

  return (
    <DashboardContent>
      <Container>
        <CustomBreadcrumbs
          heading="Receipt Details"
          links={[
            { name: 'Dashboard', href: paths.dashboard.root },
            { name: 'Receipts', href: paths.dashboard.receipt.root },
            { name: receipt.receiptNumber },
          ]}
          sx={{ mb: 5 }}
        />

        <Grid container spacing={3}>
          {/* Left: Receipt Image (50%) */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom>
                Receipt Image
              </Typography>
              <Divider sx={{ my: 2 }} />
              <Box
                sx={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minHeight: 400,
                  bgcolor: 'background.neutral',
                  borderRadius: 1,
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                {receipt.imageUrl ? (
                  <Box
                    component="img"
                    src={receipt.imageUrl.startsWith('http') ? receipt.imageUrl : `${process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000'}${receipt.imageUrl}`}
                    alt={receipt.receiptNumber}
                    sx={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: 'contain',
                      cursor: 'zoom-in',
                    }}
                    onClick={() => {
                      // Simple zoom - could be enhanced with a modal
                      const img = document.createElement('img');
                      const fullImageUrl = receipt.imageUrl!.startsWith('http') 
                        ? receipt.imageUrl! 
                        : `${process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000'}${receipt.imageUrl}`;
                      img.src = fullImageUrl;
                      img.style.position = 'fixed';
                      img.style.top = '50%';
                      img.style.left = '50%';
                      img.style.transform = 'translate(-50%, -50%)';
                      img.style.maxWidth = '90vw';
                      img.style.maxHeight = '90vh';
                      img.style.zIndex = 9999;
                      img.style.cursor = 'zoom-out';
                      img.onclick = () => document.body.removeChild(img);
                      document.body.appendChild(img);
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      gap: 2,
                      color: 'text.secondary',
                    }}
                  >
                    <Iconify icon="solar:document-add-bold-duotone" width={64} />
                    <Typography variant="body2">No image available</Typography>
                  </Box>
                )}
              </Box>
            </Card>
          </Grid>

          {/* Right: Editable Form (50%) */}
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ p: 3 }}>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Receipt Information
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Grid container spacing={2}>
                    <Grid size={{ xs: 6, sm: 4 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Receipt Number
                      </Typography>
                      <Typography variant="body1">{receipt.receiptNumber}</Typography>
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Vendor"
                        value={editedReceipt?.vendor || receipt.vendor}
                        onChange={(e) =>
                          setEditedReceipt({ ...editedReceipt, vendor: e.target.value })
                        }
                        variant="outlined"
                        size="small"
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Date"
                        type="datetime-local"
                        value={editedReceipt?.date ? new Date(editedReceipt.date).toISOString().slice(0, 16) : new Date(receipt.date).toISOString().slice(0, 16)}
                        onChange={(e) =>
                          setEditedReceipt({ ...editedReceipt, date: new Date(e.target.value).toISOString() })
                        }
                        variant="outlined"
                        size="small"
                        InputLabelProps={{ shrink: true }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Category"
                        value={editedReceipt?.category || receipt.category}
                        onChange={(e) =>
                          setEditedReceipt({ ...editedReceipt, category: e.target.value })
                        }
                        variant="outlined"
                        size="small"
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Payment Method"
                        value={editedReceipt?.paymentMethod || receipt.paymentMethod}
                        onChange={(e) =>
                          setEditedReceipt({ ...editedReceipt, paymentMethod: e.target.value })
                        }
                        variant="outlined"
                        size="small"
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="Total"
                        type="number"
                        value={editedReceipt?.total || receipt.total}
                        onChange={(e) =>
                          setEditedReceipt({ ...editedReceipt, total: parseFloat(e.target.value) })
                        }
                        variant="outlined"
                        size="small"
                        InputProps={{
                          startAdornment: <Typography sx={{ mr: 1 }}>€</Typography>,
                        }}
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        fullWidth
                        label="VAT"
                        type="number"
                        value={editedReceipt?.vat || receipt.vat || 0}
                        onChange={(e) =>
                          setEditedReceipt({ ...editedReceipt, vat: parseFloat(e.target.value) })
                        }
                        variant="outlined"
                        size="small"
                        InputProps={{
                          startAdornment: <Typography sx={{ mr: 1 }}>€</Typography>,
                        }}
                      />
                    </Grid>
                    <Grid size={{ xs: 6, sm: 4 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Status
                      </Typography>
                      <Label
                        variant="soft"
                        color={receipt.status === 'verified' ? 'success' : 'warning'}
                      >
                        {receipt.status}
                      </Label>
                    </Grid>
                  </Grid>
                </Box>

                <Box>
                  <Typography variant="h6" gutterBottom>
                    Line Items
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse' }}>
                    <Box component="thead">
                      <Box component="tr" sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
                        <Box component="th" sx={{ p: 1.5, textAlign: 'left', fontWeight: 600 }}>
                          Description
                        </Box>
                        <Box component="th" sx={{ p: 1.5, textAlign: 'right', fontWeight: 600 }}>
                          Quantity
                        </Box>
                        <Box component="th" sx={{ p: 1.5, textAlign: 'right', fontWeight: 600 }}>
                          Unit Price
                        </Box>
                        <Box component="th" sx={{ p: 1.5, textAlign: 'right', fontWeight: 600 }}>
                          VAT
                        </Box>
                        <Box component="th" sx={{ p: 1.5, textAlign: 'right', fontWeight: 600 }}>
                          Total
                        </Box>
                      </Box>
                    </Box>
                    <Box component="tbody">
                      {receipt.lineItems.map((item) => (
                        <Box
                          key={item.id}
                          component="tr"
                          sx={{ borderBottom: '1px solid', borderColor: 'divider' }}
                        >
                          <Box component="td" sx={{ p: 1.5 }}>
                            {item.description}
                          </Box>
                          <Box component="td" sx={{ p: 1.5, textAlign: 'right' }}>
                            {item.quantity}
                          </Box>
                          <Box component="td" sx={{ p: 1.5, textAlign: 'right' }}>
                            {fCurrency(item.unitPrice)}
                          </Box>
                          <Box component="td" sx={{ p: 1.5, textAlign: 'right' }}>
                            {item.vat}%
                          </Box>
                          <Box component="td" sx={{ p: 1.5, textAlign: 'right', fontWeight: 600 }}>
                            {fCurrency(item.total)}
                          </Box>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                </Box>

                {receipt.notes && (
                  <Box>
                    <Typography variant="h6" gutterBottom>
                      Notes
                    </Typography>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="body2">{receipt.notes}</Typography>
                  </Box>
                )}
              </Stack>
            </Card>
          </Grid>
        </Grid>

        {/* Summary and Issues Section */}
        <Grid container spacing={3} sx={{ mt: 0 }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Stack spacing={3}>
              <Card sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Summary
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Stack spacing={2}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      Subtotal
                    </Typography>
                    <Typography variant="body1">{fCurrency(receipt.subtotal)}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      VAT
                    </Typography>
                    <Typography variant="body1" color={receipt.vat ? 'inherit' : 'error.main'}>
                      {receipt.vat ? fCurrency(receipt.vat) : 'Missing'}
                    </Typography>
                  </Box>
                  <Divider />
                  {mismatchDetails ? (
                    <>
                      {mismatchExpanded && (
                        <>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                              Expected Total
                            </Typography>
                            <Typography variant="body1" sx={{ fontWeight: 600 }}>
                              {fCurrency(mismatchDetails.expectedTotal)}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              Actual Total
                            </Typography>
                            <Typography variant="h6" sx={{ color: 'error.main' }}>
                              {fCurrency(receipt.total)}
                            </Typography>
                          </Box>
                          <Box 
                            sx={{ 
                              display: 'flex', 
                              justifyContent: 'space-between',
                              p: 1,
                              borderRadius: 1,
                              bgcolor: mismatchDetails.difference > 0 ? 'error.lighter' : 'warning.lighter'
                            }}
                          >
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              Difference
                            </Typography>
                            <Typography 
                              variant="body2" 
                              sx={{ 
                                fontWeight: 700,
                                color: mismatchDetails.difference > 0 ? 'error.main' : 'warning.main'
                              }}
                            >
                              {mismatchDetails.difference > 0 ? '+' : ''}{fCurrency(mismatchDetails.difference)}
                            </Typography>
                          </Box>
                        </>
                      )}
                      {!mismatchExpanded && (
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                            Total
                          </Typography>
                          <Typography variant="h6" sx={{ color: 'error.main' }}>
                            {fCurrency(receipt.total)}
                          </Typography>
                        </Box>
                      )}
                    </>
                  ) : (
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        Total
                      </Typography>
                      <Typography variant="h6">{fCurrency(receipt.total)}</Typography>
                    </Box>
                  )}
                </Stack>
              </Card>

              {hasIssues && (
                <Card sx={{ p: 3, bgcolor: 'error.lighter' }}>
                  <Typography variant="h6" gutterBottom color="error.main">
                    Audit Issues
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Stack spacing={1}>
                    {receipt.auditFlags.isDuplicate && (
                      <Label variant="soft" color="warning">
                        Duplicate Receipt
                      </Label>
                    )}
                    {receipt.auditFlags.hasTotalMismatch && mismatchDetails && (
                      <Box>
                        <Box
                          component="button"
                          onClick={() => setMismatchExpanded(!mismatchExpanded)}
                          sx={{
                            border: 'none',
                            background: 'none',
                            padding: 0,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.5,
                            mb: mismatchExpanded ? 1 : 0,
                            '&:hover': {
                              opacity: 0.8,
                            },
                          }}
                        >
                          <Label variant="soft" color="error">
                            Total Mismatch
                          </Label>
                          <Iconify
                            icon={mismatchExpanded ? 'solar:alt-arrow-up-bold' : 'solar:alt-arrow-down-bold'}
                            width={16}
                            sx={{ color: 'error.main' }}
                          />
                        </Box>
                        {mismatchExpanded && (
                          <Stack spacing={1} sx={{ mt: 1, pl: 1 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                Expected Total:
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                {fCurrency(mismatchDetails.expectedTotal)}
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                                Actual Total:
                              </Typography>
                              <Typography variant="body2" sx={{ fontWeight: 600, color: 'error.main' }}>
                                {fCurrency(mismatchDetails.actualTotal)}
                              </Typography>
                            </Box>
                            <Divider />
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                Difference:
                              </Typography>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  fontWeight: 700,
                                  color: mismatchDetails.difference > 0 ? 'error.main' : 'warning.main'
                                }}
                              >
                                {mismatchDetails.difference > 0 ? '+' : ''}{fCurrency(mismatchDetails.difference)}
                                {mismatchDetails.difference > 0 ? ' (over)' : ' (under)'}
                              </Typography>
                            </Box>
                          </Stack>
                        )}
                      </Box>
                    )}
                    {receipt.auditFlags.missingVAT && (
                      <Label variant="soft" color="error">
                        Missing VAT
                      </Label>
                    )}
                    {receipt.auditFlags.suspiciousCategory && (
                      <Label variant="soft" color="error">
                        Suspicious Category: {receipt.auditFlags.suspiciousCategory}
                      </Label>
                    )}
                  </Stack>
                </Card>
              )}

              <Button
                component={RouterLink}
                href={paths.dashboard.receipt.root}
                variant="outlined"
                startIcon={<Iconify icon="solar:arrow-left-bold" />}
                fullWidth
              >
                Back to Receipts
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </Container>
    </DashboardContent>
  );
}

