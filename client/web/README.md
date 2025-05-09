# Wine-AI Web Client

A React-based web interface for the Wine-AI system.

## Features

- Real-time chat interface
- Wine knowledge query and response
- Responsive design

## Getting Started

### Prerequisites

- Node.js (recommended v16+)
- npm or yarn
- Wine-AI server running

### Installation

1. Install dependencies:
   ```
   npm install
   ```
   or
   ```
   yarn
   ```

2. Start the development server:
   ```
   npm start
   ```
   or
   ```
   yarn start
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Development

The web app uses Vite for development and building. The app is set up to proxy API requests to the Wine-AI server running on http://localhost:8080.

### Building for Production

To build the app for production:

```
npm run build
```
or
```
yarn build
```

The build output will be in the `dist` folder.

### Preview Production Build

To preview the production build locally:

```
npm run preview
```
or
```
yarn preview
``` 