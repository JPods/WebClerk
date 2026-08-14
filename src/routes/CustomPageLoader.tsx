/**
 * CustomPageLoader — resolves /custom/:page to a user's custom .tsx component.
 *
 * Looks up the page name in the custom registry (src/custom/index.ts).
 * Users register pages by adding one line to the registry.
 */
import React, { Suspense } from 'react';
import { useParams } from 'react-router-dom';
import customPages from '../custom';

const CustomPageLoader: React.FC = () => {
  const { page } = useParams<{ page: string }>();

  if (!page) {
    return <div style={{ padding: 40 }}>No page specified.</div>;
  }

  const Component = customPages[page];

  if (!Component) {
    return (
      <div style={{ padding: 40 }}>
        <h2>Custom page not found: {page}</h2>
        <p>Register it in <code>src/custom/index.ts</code></p>
        <p>Available pages: {Object.keys(customPages).join(', ') || 'none'}</p>
      </div>
    );
  }

  return (
    <Suspense fallback={<div style={{ padding: 40 }}>Loading...</div>}>
      <Component />
    </Suspense>
  );
};

export default CustomPageLoader;
