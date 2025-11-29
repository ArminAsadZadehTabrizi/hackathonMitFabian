'use client';

import { useMemo, useState } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';

import { useGetReceipt } from 'src/actions/receipt';
import { DashboardContent } from 'src/layouts/dashboard';

import { Iconify } from 'src/components/iconify';
import { Label } from 'src/components/label';
import { EmptyContent } from 'src/components/empty-content';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';

import { fCurrency } from 'src/utils/format-number';
import { fDate, fTime } from 'src/utils/format-time';

// ----------------------------------------------------------------------

type Props = {
  id: string;
};

export function ReceiptDetailsView({ id }: Props) {
  const { receipt, receiptLoading } = useGetReceipt(id);
  const [mismatchExpanded, setMismatchExpanded] = useState(false);

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
          <Grid size={{ xs: 12, md: 8 }}>
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
                    <Grid size={{ xs: 6, sm: 4 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Vendor
                      </Typography>
                      <Typography variant="body1">{receipt.vendor}</Typography>
                    </Grid>
                    <Grid size={{ xs: 6, sm: 4 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Date
                      </Typography>
                      <Typography variant="body1">
                        {fDate(receipt.date)} {fTime(receipt.date)}
                      </Typography>
                    </Grid>
                    <Grid size={{ xs: 6, sm: 4 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Category
                      </Typography>
                      <Label variant="soft">{receipt.category}</Label>
                    </Grid>
                    <Grid size={{ xs: 6, sm: 4 }}>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        Payment Method
                      </Typography>
                      <Typography variant="body1">{receipt.paymentMethod}</Typography>
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

