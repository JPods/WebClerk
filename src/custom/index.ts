/**
 * Custom page registry — maps component names to lazy imports.
 *
 * When a Report record has purpose='custom-page' and config.component='MyPage',
 * the router looks up 'MyPage' here and renders it.
 *
 * To add a page: create your .tsx in custom/pages/, then add one line below.
 */
import { lazy } from 'react';

const customPages: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  SegaPartsPage: lazy(() => import('./pages/SegaPartsPage')),
};

export default customPages;
