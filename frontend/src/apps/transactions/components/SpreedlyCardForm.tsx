/**
 * SpreedlyCardForm — Secure card entry via Spreedly hosted fields (iFrame).
 *
 * Card data never touches WC3 JavaScript. Spreedly's SDK renders secure
 * iframes for card number and CVV. On submit, the SDK tokenizes the card
 * and returns a payment_method_token. We pass that token to our backend.
 *
 * Security: Token-in-a-token. WC3 stores a reference to Spreedly's token,
 * which references the card. WC3 never sees or stores card numbers.
 *
 * Usage:
 *   <SpreedlyCardForm
 *     invoiceId={123}
 *     amount={50.00}
 *     onSuccess={(paymentId) => { ... }}
 *     onCancel={() => { ... }}
 *   />
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { fetchGatewayConfig, processGatewayPayment } from '../models/payment/services/paymentApi';
import { FaLock, FaSpinner } from 'react-icons/fa';
import { formatCurrency } from '@/utils/stringUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SpreedlyCardFormProps {
  invoiceId: number;
  amount: number;
  customerName?: string;
  onSuccess?: (paymentId: number) => void;
  onCancel?: () => void;
}

// Spreedly iFrame SDK global type
declare global {
  interface Window {
    Spreedly: {
      init: (envKey: string, opts: Record<string, unknown>) => void;
      on: (event: string, callback: (...args: unknown[]) => void) => void;
      tokenizeCreditCard: (data: Record<string, string>) => void;
      removeHandlers: () => void;
    };
  }
}

// ---------------------------------------------------------------------------
// SDK loader
// ---------------------------------------------------------------------------

let sdkPromise: Promise<void> | null = null;

function loadSpreedlySDK(): Promise<void> {
  if (sdkPromise) return sdkPromise;
  if (window.Spreedly) return Promise.resolve();

  sdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://core.spreedly.com/iframe/iframe-v1.min.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Spreedly SDK'));
    document.head.appendChild(script);
  });
  return sdkPromise;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SpreedlyCardForm({
  invoiceId,
  amount,
  customerName,
  onSuccess,
  onCancel,
}: SpreedlyCardFormProps) {
  const dispatch = useDispatch();
  const [envKey, setEnvKey] = useState('');
  const [testMode, setTestMode] = useState(true);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');

  // Cardholder fields (these are NOT sensitive — name and billing info)
  const [fullName, setFullName] = useState(customerName || '');
  const [month, setMonth] = useState('');
  const [year, setYear] = useState('');

  const initRef = useRef(false);

  // Fetch gateway config
  useEffect(() => {
    fetchGatewayConfig()
      .then((config) => {
        setEnvKey(config.environment_key);
        setTestMode(config.test_mode);
        if (!config.environment_key) {
          setError('Payment gateway not configured. Contact administrator.');
        }
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load payment configuration.');
        setLoading(false);
      });
  }, []);

  // Initialize Spreedly SDK once we have the env key
  useEffect(() => {
    if (!envKey || initRef.current) return;
    initRef.current = true;

    loadSpreedlySDK()
      .then(() => {
        const S = window.Spreedly;

        S.init(envKey, {
          numberEl: 'spreedly-number',
          cvvEl: 'spreedly-cvv',
        });

        S.on('ready', () => {
          setReady(true);
          // Style the iframes to match our design
          S.on('fieldEvent', () => {}); // required listener
        });

        S.on('errors', (errors: unknown) => {
          setProcessing(false);
          const errList = errors as Array<{ message: string }>;
          const msg = errList?.map((e) => e.message).join(', ') || 'Card validation failed';
          setError(msg);
        });

        S.on('paymentMethod', (token: unknown, pmData: unknown) => {
          const t = token as string;
          handleTokenReceived(t);
        });
      })
      .catch(() => {
        setError('Failed to load secure payment form.');
      });

    return () => {
      if (window.Spreedly) {
        try { window.Spreedly.removeHandlers(); } catch { /* ok */ }
      }
    };
  }, [envKey]);

  // Handle token from Spreedly SDK
  const handleTokenReceived = useCallback(async (paymentMethodToken: string) => {
    try {
      const result = await processGatewayPayment(invoiceId, amount, paymentMethodToken);
      if (result.status === 'completed') {
        dispatch(showToast({
          message: `Payment of ${formatCurrency(amount)} processed successfully`,
          type: 'success',
        }));
        onSuccess?.(result.payment_id);
      } else if (result.status === 'failed') {
        setError(result.message || 'Payment was declined.');
      } else {
        // pending — webhook will confirm
        dispatch(showToast({
          message: 'Payment submitted — awaiting confirmation',
          type: 'info',
        }));
        onSuccess?.(result.payment_id);
      }
    } catch (e: any) {
      const msg = e?.response?.data?.error || e?.message || 'Payment processing failed';
      setError(msg);
    } finally {
      setProcessing(false);
    }
  }, [invoiceId, amount, dispatch, onSuccess]);

  // Submit — triggers Spreedly tokenization
  const handleSubmit = useCallback(() => {
    if (!ready || processing) return;
    setError('');
    setProcessing(true);

    const [firstName, ...rest] = fullName.trim().split(' ');
    const lastName = rest.join(' ') || firstName;

    window.Spreedly.tokenizeCreditCard({
      first_name: firstName,
      last_name: lastName,
      month: month.padStart(2, '0'),
      year: year.length === 2 ? `20${year}` : year,
    });
  }, [ready, processing, fullName, month, year]);

  const inputClass =
    'w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm';
  const labelClass =
    'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1';

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 text-slate-400">
        <FaSpinner className="animate-spin mr-2" /> Loading secure payment form...
      </div>
    );
  }

  if (error && !envKey) {
    return (
      <div className="p-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg">
        {error}
      </div>
    );
  }

  return (
    <div data-wc="spreedly-card-form" className="space-y-4">
      {/* Test mode banner */}
      {testMode && (
        <div className="px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
          Test mode — no real charges. Use card 4111 1111 1111 1111.
        </div>
      )}

      {/* Amount display */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
        <span className="text-sm text-slate-500 dark:text-slate-400">Amount to charge:</span>
        <span className="text-lg font-semibold text-slate-900 dark:text-white">
          ${amount.toFixed(2)}
        </span>
      </div>

      {/* Cardholder name */}
      <div>
        <label className={labelClass}>Cardholder Name</label>
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Name on card"
          className={inputClass}
        />
      </div>

      {/* Spreedly hosted field — Card Number */}
      <div>
        <label className={labelClass}>Card Number</label>
        <div
          id="spreedly-number"
          className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 overflow-hidden"
        />
      </div>

      {/* Expiry + CVV row */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className={labelClass}>Month</label>
          <input
            type="text"
            value={month}
            onChange={(e) => setMonth(e.target.value.replace(/\D/g, '').slice(0, 2))}
            placeholder="MM"
            maxLength={2}
            className={inputClass}
          />
        </div>
        <div>
          <label className={labelClass}>Year</label>
          <input
            type="text"
            value={year}
            onChange={(e) => setYear(e.target.value.replace(/\D/g, '').slice(0, 4))}
            placeholder="YYYY"
            maxLength={4}
            className={inputClass}
          />
        </div>
        <div>
          <label className={labelClass}>CVV</label>
          <div
            id="spreedly-cvv"
            className="w-full h-10 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 overflow-hidden"
          />
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="px-3 py-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-1 text-xs text-slate-400">
          <FaLock size={10} />
          <span>Secured by Spreedly — card data never touches our servers</span>
        </div>
        <div className="flex gap-2">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!ready || processing || !fullName || !month || !year}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {processing ? (
              <>
                <FaSpinner className="animate-spin" size={14} />
                Processing...
              </>
            ) : (
              <>
                <FaLock size={12} />
                Pay ${amount.toFixed(2)}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
