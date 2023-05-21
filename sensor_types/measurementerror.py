class MeasurementError(Exception):
  def __init__(self, message="Unable to read measurement data from sensor"):
        self.message = message
        super().__init__(self.message)
