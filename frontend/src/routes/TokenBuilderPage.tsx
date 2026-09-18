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
    <Suspense fallback={<div className="p-10">Loading...</div>}>
      <div className="h-screen">
        <TokenBuilder model={model} />
      </div>
    </Suspense>
  );
};

export default TokenBuilderPage;
