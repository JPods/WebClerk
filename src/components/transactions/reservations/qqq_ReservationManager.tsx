/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useState, useEffect } from 'react';
import { useWCAPI } from '../../../hooks/useWCAPI';
import { useAuditTrail } from '../../../hooks/useAuditTrail';

export interface ReservationManagerProps {
  itemId: number;
  itemName: string;
  availableQuantity: number;
  onReservationComplete?: (reservation: any) => void;
}

export const ReservationManager: React.FC<ReservationManagerProps> = ({
  itemId,
  itemName,
  availableQuantity,
  onReservationComplete,
}) => {
  const { get, create } = useWCAPI();
  const [loading, setLoading] = useState(false);
  const [reservations, setReservations] = useState<any[]>([]);
  const [newReservation, setNewReservation] = useState({
    quantity: 1,
    ttlMinutes: 15, // 15 minutes default
    reason: '',
  });

  const { addEntry } = useAuditTrail(0, 'inventory_reservation');

  useEffect(() => {
    loadReservations();
  }, [itemId]);

  const loadReservations = async () => {
    try {
      const response = await get('inventory_reservation', {
        item_id: itemId,
        state: 'pending',
        order_by: '-expires_at',
      });

      if (response?.results) {
        setReservations(response.results);
      }
    } catch (error) {
      console.error('Failed to load reservations:', error);
    }
  };

  const createReservation = async () => {
    if (newReservation.quantity > availableQuantity) {
      alert('Requested quantity exceeds available stock');
      return;
    }

    setLoading(true);
    try {
      const reservationData = {
        item_id: itemId,
        quantity: newReservation.quantity,
        ttl_seconds: newReservation.ttlMinutes * 60,
        reason: newReservation.reason,
        context: {
          created_via: 'react_ui',
          item_name: itemName,
        },
      };

      const response = await create('inventory_reservation', reservationData);

      if (response?.record) {
        await addEntry('created', {
          item_id: itemId,
          quantity: newReservation.quantity,
          ttl_minutes: newReservation.ttlMinutes,
          reason: newReservation.reason,
        });

        setReservations(prev => [response.record, ...prev]);
        setNewReservation({ quantity: 1, ttlMinutes: 15, reason: '' });
        onReservationComplete?.(response.record);
      }
    } catch (error) {
      console.error('Failed to create reservation:', error);
    } finally {
      setLoading(false);
    }
  };

  const cancelReservation = async (reservationId: number) => {
    try {
      // Note: This would need a cancel endpoint or update to cancelled state
      await addEntry('cancelled', { reservation_id: reservationId });
      setReservations(prev => prev.filter(r => r.id !== reservationId));
    } catch (error) {
      console.error('Failed to cancel reservation:', error);
    }
  };

  const formatExpiry = (expiresAt: string) => {
    const expiry = new Date(expiresAt);
    const now = new Date();
    const diffMinutes = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60));

    if (diffMinutes < 0) {
      return 'Expired';
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m remaining`;
    } else {
      const hours = Math.floor(diffMinutes / 60);
      return `${hours}h ${diffMinutes % 60}m remaining`;
    }
  };

  const getReservationStatusColor = (expiresAt: string) => {
    const expiry = new Date(expiresAt);
    const now = new Date();
    const diffMinutes = (expiry.getTime() - now.getTime()) / (1000 * 60);

    if (diffMinutes < 0) return 'text-red-600 bg-red-100';
    if (diffMinutes < 5) return 'text-orange-600 bg-orange-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="reservation-manager bg-white p-6 rounded-lg shadow-sm border">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Inventory Reservations - {itemName}
        </h2>
        <div className="text-sm text-gray-600">
          Available: <span className="font-medium">{availableQuantity}</span> units
        </div>
      </div>

      {/* Create New Reservation */}
      <div className="bg-gray-50 p-4 rounded-lg mb-6">
        <h3 className="text-lg font-medium text-gray-800 mb-4">Create Reservation</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Quantity
            </label>
            <input
              type="number"
              min="1"
              max={availableQuantity}
              value={newReservation.quantity}
              onChange={(e) => setNewReservation(prev => ({
                ...prev,
                quantity: parseInt(e.target.value) || 1
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Hold Time (minutes)
            </label>
            <select
              value={newReservation.ttlMinutes}
              onChange={(e) => setNewReservation(prev => ({
                ...prev,
                ttlMinutes: parseInt(e.target.value)
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={5}>5 minutes</option>
              <option value={15}>15 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={60}>1 hour</option>
              <option value={120}>2 hours</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Reason
            </label>
            <input
              type="text"
              placeholder="Cart reservation, etc."
              value={newReservation.reason}
              onChange={(e) => setNewReservation(prev => ({
                ...prev,
                reason: e.target.value
              }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <button
          onClick={createReservation}
          disabled={loading || newReservation.quantity > availableQuantity}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create Reservation'}
        </button>
      </div>

      {/* Existing Reservations */}
      <div>
        <h3 className="text-lg font-medium text-gray-800 mb-4">Active Reservations</h3>

        {reservations.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No active reservations
          </div>
        ) : (
          <div className="space-y-3">
            {reservations.map((reservation) => (
              <div key={reservation.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center space-x-4">
                    <div>
                      <div className="font-medium text-gray-800">
                        {reservation.quantity} units
                      </div>
                      <div className="text-sm text-gray-600">
                        {reservation.reason || 'No reason provided'}
                      </div>
                    </div>

                    <div className={`px-2 py-1 rounded-full text-xs font-medium ${getReservationStatusColor(reservation.expires_at)}`}>
                      {formatExpiry(reservation.expires_at)}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => cancelReservation(reservation.id)}
                  className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700"
                >
                  Cancel
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};