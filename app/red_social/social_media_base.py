from abc import ABC, abstractmethod

class SocialMediaBase(ABC):
    """
    Clase abstracta base para todos los servicios de redes sociales.
    
    Esta clase define la interfaz común que todos los servicios
    de redes sociales deben implementar.
    
    Patrón de diseño: Template Method
    - create_prompt() es el método template (definido aquí)
    - _define_prompt() es el método abstracto (cada subclase lo implementa)
    
    Atributos:
        platform_name (str): Nombre de la plataforma (facebook, instagram, etc.)
    
    Ejemplo de uso:
        >>> fb_service = FacebookService()
        >>> prompt = fb_service.create_prompt("quiero contenido de retiro")
        >>> print(fb_service.get_platform_name())
        'facebook'
    """
    
    def __init__(self):
        """
        Inicializa el servicio de red social.
        Extrae automáticamente el nombre de la plataforma del nombre de la clase.
        
        Ejemplo:
            FacebookService -> 'facebook'
            InstagramService -> 'instagram'
        """
        # Extrae el nombre: FacebookService -> facebook
        self.platform_name = self.__class__.__name__.replace('Service', '').lower()
    
    @abstractmethod
    def _define_prompt(self, mensaje_usuario: str) -> str:
        """
        Método abstracto que DEBE ser implementado por cada subclase.
        
        Define el prompt específico de cada red social con todas
        sus reglas, especificaciones y formato de respuesta.
        
        Args:
            mensaje_usuario (str): Mensaje original del usuario solicitando contenido
            
        Returns:
            str: El prompt completo del sistema para esta red social
            
        Raises:
            NotImplementedError: Si la subclase no implementa este método
            
        Ejemplo de implementación en subclase:
            def _define_prompt(self, mensaje_usuario: str) -> str:
                return f"Eres experto en Facebook... Usuario: {mensaje_usuario}"
        """
        pass
    
    # ========================================
    # MÉTODOS PÚBLICOS (Template Methods)
    # ========================================
    
    def create_prompt(self, mensaje_usuario: str) -> str:
        """
        Método template que crea el prompt completo.
        
        Este método usa internamente _define_prompt() que es
        implementado por cada subclase específica.
        
        Args:
            mensaje_usuario (str): Mensaje del usuario
            
        Returns:
            str: Prompt completo listo para enviar a OpenAI
            
        Ejemplo:
            >>> service = FacebookService()
            >>> prompt = service.create_prompt("contenido sobre becas")
            >>> # prompt contiene el prompt completo de Facebook
        """
        return self._define_prompt(mensaje_usuario)
    
    def get_platform_name(self) -> str:
        """
        Obtiene el nombre de la plataforma.
        
        Returns:
            str: Nombre de la plataforma ('facebook', 'instagram', etc.)
            
        Ejemplo:
            >>> service = FacebookService()
            >>> service.get_platform_name()
            'facebook'
        """
        return self.platform_name
    
    # ========================================
    # MÉTODOS MÁGICOS
    # ========================================
    
    def __repr__(self) -> str:
        """
        Representación en string del objeto para debugging.
        
        Returns:
            str: Representación del servicio
            
        Ejemplo:
            >>> service = FacebookService()
            >>> print(service)
            <FacebookService platform=facebook>
        """
        return f"<{self.__class__.__name__} platform={self.platform_name}>"
    
    def __str__(self) -> str:
        """
        Representación legible del objeto.
        
        Returns:
            str: Nombre legible del servicio
        """
        return f"{self.platform_name.capitalize()} Service"