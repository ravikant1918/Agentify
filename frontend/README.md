# Agentify - Modern React Frontend

A complete transformation of Agentify from HTML/HTMX to a modern React application with advanced UI components, toast notifications, modals, and state management.

## 🎨 New Features

### Modern React UI
- **Component-based architecture** with reusable components
- **Zustand state management** for efficient state handling
- **React Router** for seamless navigation
- **Tailwind CSS** with custom design system
- **Framer Motion** for smooth animations
- **Headless UI** for accessible components

### Enhanced UX
- **Toast notifications** with react-hot-toast
- **Modal dialogs** for better user interactions
- **Loading states** and skeleton screens
- **Auto-resizing text areas**
- **Responsive design** for all screen sizes
- **Dark mode support** with persistent settings

### Better Architecture
- **TypeScript support** for better development experience
- **API layer** with axios for HTTP requests
- **Error handling** with proper user feedback
- **Hot reloading** for fast development
- **Production builds** with Vite

## 🏗️ Project Structure

```
agentify/
├── frontend/                 # React application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── MessagesList.tsx
│   │   │   └── ChatInput.tsx
│   │   ├── pages/           # Page components
│   │   │   ├── ChatPage.tsx
│   │   │   └── ConfigPage.tsx
│   │   ├── store/           # Zustand stores
│   │   │   ├── ui.ts
│   │   │   ├── chat.ts
│   │   │   └── mcp.ts
│   │   ├── utils/           # Utilities and API
│   │   │   ├── index.ts
│   │   │   └── api.ts
│   │   ├── App.tsx          # Main app component
│   │   └── main.tsx         # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── postcss.config.js
├── src/                     # Backend Python code
├── templates/               # Legacy templates (kept for compatibility)
├── static/                  # Static assets
├── app.py                   # FastAPI backend
├── dev.sh                   # Development script
└── README.md                # This file
```

## 🚀 Quick Start

### Option 1: Use Development Script (Recommended)
```bash
./dev.sh
```

This starts both backend and frontend servers with hot reloading.

### Option 2: Manual Setup

1. **Start Backend Server:**
```bash
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

2. **Start Frontend Development Server:**
```bash
cd frontend
npm install
npm run dev
```

3. **Build Production Frontend:**
```bash
cd frontend
npm run build
```

## 🌐 Access Points

- **Production App**: http://localhost:8001 (Served by FastAPI)
- **Development App**: http://localhost:3000 (React dev server with hot reload)
- **API Documentation**: http://localhost:8001/docs

## 🎯 API Endpoints

### Chat API
- `GET /api/threads` - List all chat threads
- `POST /api/threads` - Create new thread
- `DELETE /api/threads/{id}` - Delete thread
- `GET /api/threads/{id}/messages` - Get thread messages
- `POST /api/chat` - Send chat message

### MCP API
- `GET /api/mcp/status` - Get MCP connection status
- `GET /api/mcp/servers` - List MCP servers
- `POST /api/mcp/servers` - Add MCP server
- `DELETE /api/mcp/servers/{id}` - Delete MCP server
- `POST /api/mcp/servers/{id}/connect` - Connect to server
- `POST /api/mcp/servers/{id}/disconnect` - Disconnect from server

## 🎨 Component Library

### Core Components
- **Button**: Variants (primary, secondary, outline, ghost) with loading states
- **Input**: With labels, errors, and helper text
- **Modal**: Responsive modals with backdrop and animations
- **Toast**: Success, error, and info notifications

### Chat Components
- **MessagesList**: Displays chat messages with typing indicators
- **ChatInput**: Auto-resizing textarea with send button
- **Sidebar**: Thread list with search and management
- **Navbar**: Navigation with status indicators and theme toggle

## 🎛️ State Management

### UI Store (`useUIStore`)
- Dark mode preference
- Sidebar open/closed state
- Global UI settings

### Chat Store (`useChatStore`)
- Active threads and messages
- Current thread selection
- Loading and typing states
- Message sending and thread management

### MCP Store (`useMCPStore`)
- MCP server configurations
- Connection status
- Server management operations

## 🛠️ Development

### Available Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint errors

### Tech Stack
- **React 18** with hooks and functional components
- **TypeScript** for type safety
- **Vite** for fast builds and hot reloading
- **Tailwind CSS** for styling
- **Zustand** for state management
- **React Router Dom** for routing
- **React Hot Toast** for notifications
- **Headless UI** for accessible components
- **Heroicons** for beautiful icons
- **Framer Motion** for animations

## 🎨 Design System

### Colors
- **Primary**: Blue tones (#0ea5e9)
- **Gray Scale**: Comprehensive gray palette
- **Status Colors**: Green (success), Red (error), Yellow (warning)

### Typography
- **Font**: System font stack for optimal performance
- **Sizes**: Consistent scale from xs to 6xl
- **Weights**: Regular, medium, semibold, bold

### Spacing
- **Consistent scale**: 0.25rem increments
- **Responsive**: Mobile-first approach
- **Grid**: Flexbox and CSS Grid layouts

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:
```
LLM_PROVIDER=azure
MCP_URL=http://localhost:8000
GOOGLE_API_KEY=your_api_key_here
```

### Vite Configuration
- **Proxy**: API calls proxied to backend
- **Aliases**: Clean import paths
- **Build**: Optimized for production

## 📱 Responsive Design

- **Mobile**: Optimized for touch interfaces
- **Tablet**: Improved layout for medium screens
- **Desktop**: Full-featured experience
- **Dark Mode**: System preference detection

## 🚀 Production Deployment

1. **Build Frontend:**
```bash
cd frontend && npm run build
```

2. **Start Production Server:**
```bash
uvicorn app:app --host 0.0.0.0 --port 8001
```

The built React app is automatically served by FastAPI from `/frontend/dist/`.

## 🔄 Migration Notes

- **Backwards Compatibility**: Old HTML templates still work
- **API Compatibility**: All existing APIs remain functional
- **Gradual Migration**: Can migrate features incrementally
- **Dual Serving**: Both old and new UIs can coexist

## 🎉 What's New

✅ **Modern React Architecture**  
✅ **Beautiful Toast Notifications**  
✅ **Smooth Modal Dialogs**  
✅ **Advanced State Management**  
✅ **Responsive Design**  
✅ **Dark Mode Support**  
✅ **TypeScript Integration**  
✅ **Hot Reloading**  
✅ **Production Builds**  
✅ **API Documentation**  

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.