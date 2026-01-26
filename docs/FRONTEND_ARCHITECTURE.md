# Frontend Architecture Documentation

**BioVaram EV Analysis Platform - React/Next.js Frontend**

*Last Updated: January 2026*

---

## 📁 Directory Structure

```
ev-analysis-platform/
├── app/                      # Next.js App Router (pages)
├── components/               # React components
├── lib/                      # Utilities & API client
├── hooks/                    # Custom React hooks
├── public/                   # Static assets
├── styles/                   # Global CSS
└── types/                    # TypeScript definitions
```

---

## 🏗 Architecture Overview

### Tech Stack

| Technology | Purpose | Version |
|------------|---------|---------|
| **Next.js** | React framework | 14.x |
| **React** | UI library | 18.x |
| **TypeScript** | Type safety | 5.x |
| **Tailwind CSS** | Styling | 3.x |
| **Shadcn/UI** | Component library | Latest |
| **Recharts** | Charts | 2.x |
| **NextAuth.js** | Authentication | 4.x |
| **Zustand** | State management | 4.x |

---

## 📱 App Directory (`app/`)

Next.js 14 App Router structure:

```
app/
├── page.tsx              # Main dashboard (/)
├── layout.tsx            # Root layout with providers
├── globals.css           # Global styles
│
├── (auth)/               # Auth group (shared layout)
│   ├── layout.tsx        # Auth pages layout
│   ├── login/
│   │   └── page.tsx      # Login page (/login)
│   └── signup/
│       └── page.tsx      # Signup page (/signup)
│
└── api/                  # API routes
    ├── auth/
    │   └── [...nextauth]/
    │       └── route.ts  # NextAuth handler
    └── research/
        └── route.ts      # AI chat proxy
```

### Main Page (`page.tsx`)

The dashboard with tabbed interface:

```tsx
export default function Home() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1">
        <Header />
        <TabNavigation />
        {/* Tab content based on selected tab */}
      </main>
    </div>
  );
}
```

---

## 🧩 Components (`components/`)

### Directory Structure

```
components/
├── flow-cytometry/       # FCS analysis components
│   ├── fcs-tab.tsx       # Main FCS tab container
│   ├── file-upload.tsx   # FCS file upload
│   ├── channel-selector.tsx
│   ├── analysis-results.tsx
│   └── export-options.tsx
│
├── nta/                  # NTA analysis components
│   ├── nta-tab.tsx       # Main NTA tab container
│   ├── nta-upload.tsx    # NTA file upload
│   └── nta-analysis-results.tsx
│
├── cross-compare/        # Comparison components
│   ├── cross-compare-tab.tsx
│   └── comparison-chart.tsx
│
├── charts/               # Visualization components
│   ├── scatter-chart.tsx
│   ├── histogram-chart.tsx
│   ├── overlay-histogram-chart.tsx
│   ├── density-plot.tsx
│   └── size-distribution-chart.tsx
│
├── dashboard/            # Dashboard components
│   ├── dashboard-tab.tsx
│   └── sample-overview.tsx
│
├── research-chat/        # AI chat components
│   └── research-chat-tab.tsx
│
├── ui/                   # Shadcn/UI base components
│   ├── button.tsx
│   ├── card.tsx
│   ├── input.tsx
│   ├── select.tsx
│   ├── tabs.tsx
│   └── ...
│
├── sidebar.tsx           # Navigation sidebar
├── header.tsx            # Top header bar
├── tab-navigation.tsx    # Tab switcher
├── previous-analyses.tsx # Analysis browser
├── sample-details-modal.tsx
├── error-boundary.tsx
├── loading-skeletons.tsx
└── empty-states.tsx
```

### Key Components

#### FCS Tab (`flow-cytometry/fcs-tab.tsx`)

Main container for flow cytometry analysis:

```tsx
export function FcsTab() {
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<FCSResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  async function handleUpload(file: File) {
    setIsLoading(true);
    const data = await uploadFCSFile(file);
    setResults(data);
    setIsLoading(false);
  }
  
  return (
    <div className="p-6">
      <FileUpload onUpload={handleUpload} />
      {isLoading && <LoadingSkeleton />}
      {results && <AnalysisResults data={results} />}
    </div>
  );
}
```

#### Chart Components (`charts/`)

All charts use Recharts library:

```tsx
// charts/histogram-chart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

interface HistogramChartProps {
  data: Array<{ bin: number; count: number }>;
  title?: string;
  xLabel?: string;
  yLabel?: string;
}

export function HistogramChart({ data, title, xLabel, yLabel }: HistogramChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <XAxis dataKey="bin" label={{ value: xLabel }} />
        <YAxis label={{ value: yLabel, angle: -90 }} />
        <Tooltip 
          contentStyle={{ backgroundColor: '#1e293b', color: '#f8fafc' }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Bar dataKey="count" fill="#3b82f6" />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

#### File Upload (`flow-cytometry/file-upload.tsx`)

Drag-and-drop file upload:

```tsx
export function FileUpload({ onUpload }: { onUpload: (file: File) => void }) {
  const [isDragging, setIsDragging] = useState(false);
  
  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.fcs')) {
      onUpload(file);
    }
  }
  
  return (
    <div 
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      className={`border-2 border-dashed p-8 rounded-lg ${
        isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
      }`}
    >
      <p>Drag and drop your FCS file here</p>
    </div>
  );
}
```

---

## 📚 Library (`lib/`)

### API Client (`api-client.ts`)

Handles all backend communication:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Upload FCS file
export async function uploadFCSFile(file: File, userId?: string): Promise<FCSUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (userId) formData.append('user_id', userId);
  
  const response = await fetch(`${API_BASE}/api/v1/upload/fcs`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    throw new Error('Upload failed');
  }
  
  return response.json();
}

// Get sample list
export async function getSamples(userId?: string): Promise<Sample[]> {
  const url = userId 
    ? `${API_BASE}/api/v1/samples?user_id=${userId}`
    : `${API_BASE}/api/v1/samples`;
  
  const response = await fetch(url);
  const data = await response.json();
  return data.samples;
}

// Get sample results
export async function getSampleResults(sampleId: string): Promise<AnalysisResults> {
  const response = await fetch(`${API_BASE}/api/v1/samples/${sampleId}/results/fcs`);
  return response.json();
}
```

### Authentication (`auth.ts`)

NextAuth.js configuration:

```typescript
import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';

export const authOptions = {
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: 'POST',
          body: JSON.stringify(credentials),
          headers: { 'Content-Type': 'application/json' },
        });
        const user = await res.json();
        if (user.success) return user.user;
        return null;
      },
    }),
  ],
  pages: {
    signIn: '/login',
  },
};
```

### Export Utilities (`export-utils.ts`)

PDF and Excel export:

```typescript
import jsPDF from 'jspdf';
import * as XLSX from 'xlsx';

export function exportToPDF(results: AnalysisResults, filename: string) {
  const doc = new jsPDF();
  
  doc.setFontSize(18);
  doc.text('EV Analysis Report', 20, 20);
  
  doc.setFontSize(12);
  doc.text(`Sample: ${results.filename}`, 20, 35);
  doc.text(`D50: ${results.size_distribution.d50} nm`, 20, 45);
  doc.text(`Events: ${results.statistics.total_events}`, 20, 55);
  
  doc.save(`${filename}.pdf`);
}

export function exportToExcel(results: AnalysisResults, filename: string) {
  const workbook = XLSX.utils.book_new();
  
  // Summary sheet
  const summaryData = [
    ['Metric', 'Value'],
    ['D10', results.size_distribution.d10],
    ['D50', results.size_distribution.d50],
    ['D90', results.size_distribution.d90],
  ];
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');
  
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}
```

### State Management (`store.ts`)

Zustand store for global state:

```typescript
import { create } from 'zustand';

interface AppState {
  activeTab: string;
  currentSample: Sample | null;
  setActiveTab: (tab: string) => void;
  setCurrentSample: (sample: Sample | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'dashboard',
  currentSample: null,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setCurrentSample: (sample) => set({ currentSample: sample }),
}));
```

---

## 🪝 Hooks (`hooks/`)

### useApi Hook (`use-api.ts`)

Generic API call hook with loading/error states:

```typescript
import { useState, useCallback } from 'react';

export function useApi<T>(apiFunction: (...args: any[]) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const execute = useCallback(async (...args: any[]) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiFunction(...args);
      setData(result);
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [apiFunction]);
  
  return { data, isLoading, error, execute };
}
```

### useToast Hook (`use-toast.ts`)

Toast notifications:

```typescript
import { toast } from 'sonner';

export function useToast() {
  return {
    success: (message: string) => toast.success(message),
    error: (message: string) => toast.error(message),
    info: (message: string) => toast.info(message),
  };
}
```

---

## 🎨 Styling

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3b82f6',
        secondary: '#6366f1',
        background: '#0f172a',
        surface: '#1e293b',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
```

### Common Patterns

```tsx
// Card with hover effect
<Card className="p-4 hover:shadow-lg transition-shadow">

// Primary button
<Button className="bg-primary hover:bg-primary/90">

// Form input
<Input className="bg-surface border-gray-700 focus:border-primary" />

// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
```

---

## 📝 TypeScript Types (`types/`)

### Common Types

```typescript
// types/sample.ts
interface Sample {
  id: string;
  filename: string;
  sample_type: 'fcs' | 'nta';
  upload_date: string;
  event_count: number;
  user_id: string;
}

// types/results.ts
interface SizeDistribution {
  d10: number;
  d50: number;
  d90: number;
  mean: number;
  std: number;
  mode: number;
}

interface FCSResults {
  sample_id: string;
  filename: string;
  statistics: {
    total_events: number;
    valid_events: number;
  };
  size_distribution: SizeDistribution;
  histogram: {
    bins: number[];
    counts: number[];
  };
}
```

---

## 🔄 Data Flow

```
1. User Action (e.g., upload file)
   │
   ▼
2. Component calls lib/api-client.ts function
   │
   ▼
3. API client sends request to backend
   │
   ▼
4. Backend processes and returns JSON
   │
   ▼
5. Component updates state with results
   │
   ▼
6. React re-renders with new data
```

---

## 🧪 Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Check TypeScript errors
npm run type-check

# Lint code
npm run lint

# Format code
npm run format
```

---

*For backend details, see `backend/docs/BACKEND_ARCHITECTURE.md`*
