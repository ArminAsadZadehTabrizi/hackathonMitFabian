/**
 * Next.js API Route - Proxy zu Backend
 * Löst das Problem mit SSR und Environment-Variablen
 */
import type { NextRequest} from 'next/server';

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_SERVER_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const receiptId = searchParams.get('receiptId');
    
    let url = `${BACKEND_URL}/api/receipts`;
    if (receiptId) {
      url += `?receiptId=${receiptId}`;
    }
    
    console.log(`🔗 Proxy Request to: ${url}`);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store', // Immer frische Daten
    });

    if (!response.ok) {
      console.error(`❌ Backend Error: ${response.status} ${response.statusText}`);
      return NextResponse.json(
        { error: `Backend error: ${response.status}`, url },
        { status: response.status }
      );
    }

    const data = await response.json();
    const resolvedCount = data.count ?? (Array.isArray(data.receipts) ? data.receipts.length : 0);
    console.log(`✅ Proxy Response: ${resolvedCount} receipts`);
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('❌ API Proxy Error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error', backend: BACKEND_URL },
      { status: 500 }
    );
  }
}

