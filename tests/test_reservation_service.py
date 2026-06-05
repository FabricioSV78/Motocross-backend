import unittest
from datetime import date, time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.models import Coach, CoachService, Track
from app.models.enums import ReservationStatus, Status
from app.services.reservation_service import ReservationService


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, mapping=None):
        self.mapping = mapping or {}
        self.commit = MagicMock()

    def query(self, model):
        return FakeQuery(self.mapping.get(model))


class ReservationServiceTests(unittest.TestCase):
    def setUp(self):
        self.future_date = date.today() + timedelta(days=2)
        self.track = SimpleNamespace(
            id=1,
            price_junior=40.0,
            price_senior=60.0,
            price_junior_half=25.0,
            price_senior_half=35.0,
        )
        self.track_slot = SimpleNamespace(
            track_id=1,
            date=self.future_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            capacity=10,
            pilot_category='BOTH',
            rental_type='FULL_DAY',
        )

    def test_rejects_same_day_reservations(self):
        with self.assertRaises(HTTPException) as context:
            ReservationService.calculate_reservation_cost(
                db=FakeSession(),
                track_id=1,
                reservation_date=date.today(),
                start_time=time(9, 0),
                end_time=time(12, 0),
                pilot_type='JUNIOR',
                class_type='FULL_DAY',
                participants=1,
            )

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, 'Date must be in the future')

    @patch('app.services.reservation_service.ReservationRepository.get_overlapping_reservations', return_value=[])
    @patch('app.services.reservation_service.TracksRepository')
    def test_track_only_full_day_quote_uses_track_price(self, tracks_repo_cls, _overlaps):
        tracks_repo_cls.return_value.get_covering_availability.return_value = self.track_slot
        db = FakeSession({Track: self.track})

        result = ReservationService.calculate_reservation_cost(
            db=db,
            track_id=1,
            reservation_date=self.future_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            pilot_type='SENIOR',
            class_type='FULL_DAY',
            participants=1,
        )

        self.assertEqual(result['track_price'], 60.0)
        self.assertIsNone(result['coach_price'])
        self.assertEqual(result['total'], 60.0)
        self.assertTrue(result['availability_available'])

    @patch('app.services.reservation_service.ReservationRepository.get_overlapping_reservations', return_value=[])
    @patch('app.services.reservation_service.TracksRepository')
    def test_half_day_falls_back_to_half_of_full_price(self, tracks_repo_cls, _overlaps):
        tracks_repo_cls.return_value.get_covering_availability.return_value = self.track_slot
        track = SimpleNamespace(**self.track.__dict__)
        track.price_junior_half = None
        db = FakeSession({Track: track})

        result = ReservationService.calculate_reservation_cost(
            db=db,
            track_id=1,
            reservation_date=self.future_date,
            start_time=time(9, 0),
            end_time=time(13, 0),
            pilot_type='JUNIOR',
            class_type='HALF_DAY',
            participants=1,
        )

        self.assertEqual(result['track_price'], 20.0)
        self.assertEqual(result['total'], 20.0)
        self.assertTrue(result['availability_available'])

    def test_coach_booking_requires_track_reservation_type(self):
        db = FakeSession({Track: self.track})

        with self.assertRaises(HTTPException) as context:
            ReservationService.calculate_reservation_cost(
                db=db,
                track_id=1,
                reservation_date=self.future_date,
                start_time=time(9, 0),
                end_time=time(12, 0),
                pilot_type='JUNIOR',
                coach_id=5,
                class_type='HOURLY',
                mode='ONE_TO_ONE',
                participants=1,
            )

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(
            context.exception.detail,
            'You must provide track_reservation_type when booking with a coach',
        )

    @patch('app.services.reservation_service.TracksRepository')
    @patch('app.services.reservation_service.ReservationRepository.get_overlapping_reservations')
    def test_track_capacity_accounts_for_existing_overlaps(self, overlaps_mock, tracks_repo_cls):
        track_slot = SimpleNamespace(**self.track_slot.__dict__)
        track_slot.capacity = 3
        tracks_repo_cls.return_value.get_covering_availability.return_value = track_slot
        overlaps_mock.return_value = [
            SimpleNamespace(participants=2),
            SimpleNamespace(participants=1),
        ]
        db = FakeSession({Track: self.track})

        result = ReservationService.calculate_reservation_cost(
            db=db,
            track_id=1,
            reservation_date=self.future_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            pilot_type='SENIOR',
            class_type='FULL_DAY',
            participants=1,
        )

        self.assertFalse(result['availability_available'])
        self.assertEqual(result['total'], 60.0)

    @patch('app.services.reservation_service.ReservationRepository.get_coach_reservations_overlap', return_value=[])
    @patch('app.services.reservation_service.ReservationRepository.get_overlapping_reservations', return_value=[])
    @patch('app.services.reservation_service.CoachSettingsRepository')
    @patch('app.services.reservation_service.TracksRepository')
    def test_hourly_coach_booking_calculates_track_plus_coach(
        self,
        tracks_repo_cls,
        coach_settings_repo_cls,
        _track_overlaps,
        _coach_overlaps,
    ):
        tracks_repo_cls.return_value.get_covering_availability.return_value = self.track_slot
        coach_settings_repo_cls.return_value.get_covering_availability.return_value = SimpleNamespace(
            date=self.future_date,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        coach = SimpleNamespace(id=7, status=Status.APPROVED.value)
        coach_service = SimpleNamespace(price=70.0, max_students=1)
        db = FakeSession({
            Track: self.track,
            Coach: coach,
            CoachService: coach_service,
        })

        result = ReservationService.calculate_reservation_cost(
            db=db,
            track_id=1,
            reservation_date=self.future_date,
            start_time=time(9, 0),
            end_time=time(12, 0),
            pilot_type='SENIOR',
            coach_id=7,
            class_type='HOURLY',
            track_reservation_type='FULL_DAY',
            mode='ONE_TO_ONE',
            participants=1,
        )

        self.assertEqual(result['track_price'], 60.0)
        self.assertEqual(result['coach_price'], 210.0)
        self.assertEqual(result['total'], 270.0)
        self.assertTrue(result['availability_available'])

    @patch.object(ReservationService, 'calculate_reservation_cost')
    @patch('app.services.reservation_service.ReservationRepository.update_reservation_status')
    @patch('app.services.reservation_service.ReservationRepository.create_reservation')
    def test_direct_confirm_creates_confirmed_reservation(
        self,
        create_reservation_mock,
        update_status_mock,
        calculate_cost_mock,
    ):
        calculate_cost_mock.return_value = {
            'track_price': 60.0,
            'coach_price': None,
            'subtotal': 60.0,
            'tax': 0.0,
            'total': 60.0,
            'currency': 'AUD',
            'availability_available': True,
            'total_duration_hours': 8.0,
        }
        create_reservation_mock.return_value = SimpleNamespace(id=99)
        update_status_mock.return_value = SimpleNamespace(id=99, status=ReservationStatus.CONFIRMED)
        db = FakeSession()

        result = ReservationService.create_reservation_without_payment(
            db=db,
            user_id=12,
            track_id=1,
            reservation_date=self.future_date,
            start_time=time(9, 0),
            end_time=time(17, 0),
            pilot_type='SENIOR',
            class_type='FULL_DAY',
            participants=1,
        )

        self.assertEqual(result['reservation_id'], 99)
        self.assertEqual(result['status'], ReservationStatus.CONFIRMED)
        create_reservation_mock.assert_called_once()
        update_status_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
