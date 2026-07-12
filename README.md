# Odoo Asset Management System

A modern asset management application built with TanStack Start, React, and Python backend, designed for efficient tracking and management of organizational assets.

## Tech Stack

### Frontend
- **React** 19.2.0 - UI library
- **TanStack Router** - Type-safe routing
- **TanStack Start** - Full-stack React framework
- **TanStack Query** - Data fetching and caching
- **TypeScript** - Type safety
- **Tailwind CSS** 4.2.1 - Styling
- **Radix UI** - Accessible component primitives
- **React Hook Form** - Form management
- **Zod** - Schema validation
- **Recharts** - Data visualization
- **Vite** - Build tool

### Backend
- **Python** 3.12
- **pytest** - Testing framework

### Development Tools
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **TypeScript ESLint** - TypeScript-specific linting

## Installation

### Prerequisites
- Node.js (v18 or higher)
- Python 3.12
- npm or yarn

### Frontend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd odoo-asset
```

2. Install frontend dependencies:
```bash
npm install
```

3. Configure environment variables:
```bash
cp .env .env.local
```

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend/asset
```

2. Create a virtual environment:
```bash
python -m venv .venv
```

3. Activate the virtual environment:
- Windows:
```bash
.venv\Scripts\activate
```
- Unix/MacOS:
```bash
source .venv/bin/activate
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. Configure backend environment:
```bash
cp .env.example .env
```

## Usage

### Development

Start the frontend development server:
```bash
npm run dev
```

Start the backend server:
```bash
cd backend/asset
python main.py
```

### Building for Production

Build the frontend:
```bash
npm run build
```

Build for development mode:
```bash
npm run build:dev
```

Preview production build:
```bash
npm run preview
```

### Code Quality

Run linter:
```bash
npm run lint
```

Format code:
```bash
npm run format
```

## Project Structure

```
odoo-asset/
├── backend/
│   └── asset/
│       ├── .venv/          # Python virtual environment
│       ├── .env            # Backend environment variables
│       └── .env.example    # Backend environment template
├── src/                    # Frontend source code
├── .env                    # Frontend environment variables
├── package.json            # Node dependencies
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── vite.config.ts          # Vite configuration
└── README.md               # Project documentation
```

## Features

- Modern, responsive UI with Radix UI components
- Type-safe routing and data fetching
- Form validation with Zod schemas
- Data visualization with Recharts
- Comprehensive component library (dialogs, dropdowns, accordions, etc.)
- Accessible UI components
- Dark mode support
- Toast notifications with Sonner

## License

MIT License
