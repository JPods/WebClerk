/**
 * TokenBuilderPage — route wrapper that passes URL params to TokenBuilder.
 * /tokens → all models, /tokens/order → pre-selects order model.
 */
import React, { lazy, Suspense } from 'react';
import { useParams } from 'react-router-dom';

const TokenBuilder = lazy(() => import('../components/common/TokenBuilder'));

const TokenBuilderPage: React.FC = () => {
  const { model } = useParams<{ model?: string }>();
  return (
    <Suspense fallback={<div style={{ padding: 40 }}>Loading...</div>}>
      <div style={{ height: '100vh' }}>
        <TokenBuilder model={model} />
      </div>
    </Suspense>
  );
};

export default TokenBuilderPage;
