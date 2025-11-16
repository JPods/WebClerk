from common.base_views import AdminRequiredView
from rest_framework.response import Response
from rest_framework import status
from django.core.management import call_command
import io
import sys


class RefsSettingManageView(AdminRequiredView):

    def post(self, request):
        # Get command arguments from request data
        command_args = request.data.get('args', [])
        command_kwargs = request.data.get('kwargs', {})

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Call the management command
            call_command('refs_setting_manage', *command_args, **command_kwargs)
            output = captured_output.getvalue()
            return Response({
                'success': True,
                'output': output
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            sys.stdout = old_stdout