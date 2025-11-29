'use client';

import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';

import { DashboardContent } from 'src/layouts/dashboard';
import { RouterLink } from 'src/routes/components';
import { paths } from 'src/routes/paths';

import { useGetAnalytics, useGetMonthlyAnalytics, useGetCategoryAnalytics, useGetReceipts } from 'src/actions/receipt';

import { fCurrency, fShortenNumber } from 'src/utils/format-number';

import { EcommerceYearlySales } from '../../e-commerce/ecommerce-yearly-sales';
import { EcommerceSaleByGender } from '../../e-commerce/ecommerce-sale-by-gender';
import { AppWidgetSummary } from '../../app/app-widget-summary';

// ----------------------------------------------------------------------

export function OverviewBookkeepingView() {
  const theme = useTheme();
  const { analytics, analyticsLoading } = useGetAnalytics();
  const { monthly, monthlyLoading } = useGetMonthlyAnalytics();
  const { categories, categoryLoading } = useGetCategoryAnalytics();
  const { receipts, receiptsLoading } = useGetReceipts();

  // Prepare monthly chart data
  const monthlyChartData = {
    categories: monthly.map((item) => {
      // Convert "YYYY-MM" to month name
      const [year, month] = item.month.split('-');
      const date = new Date(parseInt(year), parseInt(month) - 1);
      return date.toLocaleDateString('en-US', { month: 'short' });
    }),
    series: [
      {
        name: 'Revenue',
        data: [
          {
            name: 'Total Revenue',
            data: monthly.map((item) => item.total),
          },
        ],
      },
    ],
  };

  // Prepare category pie chart data
  const categoryChartData = {
    total: categories.reduce((sum, cat) => sum + cat.total, 0),
    series: categories.map((cat) => ({
      label: cat.category || 'Uncategorized',
      value: cat.total,
    })),
  };

  // Get recent receipts (last 5)
  const recentReceipts = receipts.slice(0, 5);

  return (
    <DashboardContent maxWidth="xl">
      <Grid container spacing={3}>
        {/* Summary Cards */}
        <Grid size={{ xs: 12, md: 3 }}>
          <AppWidgetSummary
            title="Total Spending"
            percent={0}
            total={analytics?.summary.totalSpending || 0}
            chart={{
              categories: monthly.map((m) => m.month.slice(5)),
              series: monthly.map((m) => m.total),
            }}
          />
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <AppWidgetSummary
            title="Total Receipts"
            percent={0}
            total={analytics?.summary.totalReceipts || 0}
            chart={{
              colors: [theme.palette.info.main],
              categories: monthly.map((m) => m.month.slice(5)),
              series: monthly.map((m) => m.total / 100), // Scale down for visualization
            }}
          />
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <AppWidgetSummary
            title="Total VAT"
            percent={0}
            total={analytics?.summary.totalVAT || 0}
            chart={{
              colors: [theme.palette.warning.main],
              categories: monthly.map((m) => m.month.slice(5)),
              series: monthly.map((m) => m.total * 0.1), // Approximate VAT
            }}
          />
        </Grid>

        <Grid size={{ xs: 12, md: 3 }}>
          <AppWidgetSummary
            title="Avg Receipt Value"
            percent={0}
            total={analytics?.summary.avgReceiptValue || 0}
            chart={{
              colors: [theme.palette.success.main],
              categories: monthly.map((m) => m.month.slice(5)),
              series: monthly.map((m) => m.total / Math.max(monthly.length, 1)),
            }}
          />
        </Grid>

        {/* Monthly Revenue Chart */}
        <Grid size={{ xs: 12, md: 8 }}>
          <EcommerceYearlySales
            title="Monthly Revenue"
            subheader="Revenue by month"
            chart={monthlyChartData}
          />
        </Grid>

        {/* Category Pie Chart */}
        <Grid size={{ xs: 12, md: 4 }}>
          <EcommerceSaleByGender
            title="Spending by Category"
            subheader="Total spending breakdown"
            total={categoryChartData.total}
            chart={categoryChartData}
          />
        </Grid>

        {/* Recent Receipts */}
        <Grid size={{ xs: 12 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Recent Receipts
            </Typography>
            {receiptsLoading ? (
              <Typography variant="body2" sx={{ color: 'text.secondary', py: 3 }}>
                Loading receipts...
              </Typography>
            ) : recentReceipts.length === 0 ? (
              <Typography variant="body2" sx={{ color: 'text.secondary', py: 3 }}>
                No receipts found
              </Typography>
            ) : (
              <Grid container spacing={2} sx={{ mt: 1 }}>
                {recentReceipts.map((receipt) => (
                  <Grid key={receipt.id} size={{ xs: 12, sm: 6, md: 4 }}>
                    <Card
                      component={RouterLink}
                      href={paths.dashboard.receipt.details(receipt.id)}
                      sx={{
                        p: 2,
                        textDecoration: 'none',
                        '&:hover': {
                          bgcolor: 'action.hover',
                        },
                      }}
                    >
                      <Typography variant="subtitle2">{receipt.receiptNumber}</Typography>
                      <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
                        {receipt.vendor}
                      </Typography>
                      <Typography variant="h6" sx={{ mt: 1 }}>
                        {fCurrency(receipt.total)}
                      </Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {receipt.date}
                      </Typography>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
            <Button
              component={RouterLink}
              href={paths.dashboard.receipt.root}
              variant="outlined"
              sx={{ mt: 2 }}
            >
              View All Receipts
            </Button>
          </Card>
        </Grid>
      </Grid>
    </DashboardContent>
  );
}


