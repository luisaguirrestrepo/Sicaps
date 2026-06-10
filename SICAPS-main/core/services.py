from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags

def enviar_correo_institucional(subject, to_email, html_content):
    """
    Servicio reutilizable para enviar correos usando Brevo SMTP a través de Django.
    
    Args:
        subject (str): El asunto del correo.
        to_email (str): La dirección de correo del destinatario.
        html_content (str): El cuerpo del correo en formato HTML.
    
    Returns:
        bool: True si se envió correctamente, False en caso de error.
    """
    try:
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        
        print(f"✅ Correo enviado exitosamente a {to_email} vía Brevo SMTP.")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo vía Brevo SMTP a {to_email}: {str(e)}")
        return False
